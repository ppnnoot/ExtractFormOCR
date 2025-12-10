"""
REST API Server for Medical Receipt Extraction
รองรับการส่งข้อมูลทั้งแบบ image file และ OCR text
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, validator
from typing import List, Dict, Any, Optional, Union
import json
import logging
import uvicorn
import asyncio
from pathlib import Path
import tempfile
import os
import uuid
import secrets
from datetime import datetime
from fastapi import Request
from functools import wraps
from contextlib import asynccontextmanager

# Import our pipeline and security
from ai_simple_extraction import TwoStepAIPipeline
from ai_extraction import AIExtractor
from document_classifier import DocumentClassifier
from multi_ocr_adapter import MultiOCRManager
from security_module import (
    SecurityValidator, RateLimiter, AuthenticationManager,
    SecurityHeaders, SecurityLogger, PromptInjectionDetector
)
from log_manager import setup_logging
from parallel_extraction import ReceiptSplitter, BatchReceiptExtractor

# Load configuration
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# Setup logging with rotation and cleanup
log_manager = setup_logging(config['logging'])
logger = logging.getLogger(__name__)
logger.info("🚀 API Server logging initialized with rotation and cleanup")
logger.info(f"📁 Log directory: {config['logging']['log_directory']}")
logger.info(f"📅 Max retention: {config['logging']['max_days']} days")

# Setup security logger
security_logger = logging.getLogger('security')
security_logger.info("🔒 Security logging initialized")

# Debug: Save API responses to disk
SAVE_API_RESPONSES = config.get('output', {}).get('save_api_responses', False)

def save_api_response(endpoint: str, request_id: str, response_obj: Dict[str, Any], request_meta: Optional[Dict[str, Any]] = None):
    """Save API response (and minimal request metadata) to disk for mapping verification"""
    if not SAVE_API_RESPONSES:
        return
    try:
        base_dir = config.get('output', {}).get('directory', './output')
        debug_dir = os.path.join(base_dir, 'api_debug', 'responses')
        os.makedirs(debug_dir, exist_ok=True)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_endpoint = endpoint.strip('/').replace('/', '_') or 'root'
        filename = f"api_response_{safe_endpoint}_{ts}_{request_id}.json"
        path = os.path.join(debug_dir, filename)

        payload = {
            'endpoint': endpoint,
            'timestamp': datetime.now().isoformat(),
            'request_id': request_id,
            'request_meta': request_meta or {},
            'response': response_obj
        }

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        logger.info(f"📝 API response saved: {path}")
    except Exception as e:
        logger.warning(f"Failed to save API response: {e}")

def _find_document_info(node: Any) -> Optional[List[Dict[str, Any]]]:
    """Recursively find 'document_info' list in formatted JSON."""
    try:
        if isinstance(node, dict):
            if 'document_info' in node and isinstance(node['document_info'], list):
                return node['document_info']
            for v in node.values():
                found = _find_document_info(v)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = _find_document_info(item)
                if found:
                    return found
    except Exception:
        pass
    return None

def build_simple_summary(formatted_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a simple list summary of what fields were extracted."""
    expected_basic = ['hospital_name', 'hn', 'an', 'admission_date', 'gross_amount', 'patient_name', 'invoice_no', 'date_of_issue']
    doc_info = _find_document_info(formatted_data)
    fields_present: List[str] = []
    billing_items_count = 0
    try:
        if doc_info:
            for entry in doc_info:
                code = entry.get('code')
                val = entry.get('value')
                if code:
                    # billing_items is a special case
                    if code == 'billing_items':
                        try:
                            items = val if isinstance(val, list) else []
                            billing_items_count = len(items)
                        except Exception:
                            billing_items_count = 0
                    else:
                        if val not in (None, '', [], {}):
                            fields_present.append(code)
        else:
            # Fallback: look for top-level simple fields
            for key in expected_basic:
                val = formatted_data.get(key)
                if val not in (None, '', [], {}):
                    fields_present.append(key)
    except Exception:
        pass

    fields_present = sorted(set(fields_present))
    missing_expected = [c for c in expected_basic if c not in fields_present]

    return {
        'fields_present': fields_present,
        'fields_missing_expected': missing_expected,
        'billing_items_count': billing_items_count
    }

# Lifespan: initialize shared resources on startup and cleanup on shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, ai_extractor, classifier, auth_manager, ocr_adapter
    try:
        # Initialize synchronous components - FastAPI will handle this properly
        logger.info("Initializing components in lifespan...")

        # Initialize pipeline
        pipeline = TwoStepAIPipeline('config.json')
        logger.info("Two-Step AI Pipeline initialized successfully")

        # Initialize AI Extractor (V2)
        ai_extractor = AIExtractor(config)
        logger.info("AI Extractor V2 initialized successfully")

        # Initialize OCR adapter
        ocr_adapter = MultiOCRManager(config)
        logger.info(f"Multi-OCR Manager initialized: {ocr_adapter.get_available_engines()}")

        # Initialize classifier
        classifier = DocumentClassifier(config)
        logger.info("Document Classifier initialized successfully")

        # Initialize authentication manager
        secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
        auth_manager = AuthenticationManager(secret_key)
        logger.info("Authentication Manager initialized successfully")

        SecurityLogger.log_security_event(
            "SYSTEM_STARTUP",
            {"timestamp": datetime.now().isoformat()},
            "INFO"
        )

        yield
    finally:
        SecurityLogger.log_security_event(
            "SYSTEM_SHUTDOWN",
            {"timestamp": datetime.now().isoformat()},
            "INFO"
        )
        # Cleanup shared resources
        try:
            ocr_adapter = None
            classifier = None
            auth_manager = None
            pipeline = None
            ai_extractor = None
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")

# Create FastAPI app
app = FastAPI(
    title="Medical Receipt Extraction API",
    description="""
    🏥 **AI-Powered Thai Medical Receipt Extraction System**
    
    ## Features
    - 🤖 Two-Step AI Pipeline for accurate extraction
    - 📋 Support 5 Medical Document Types (B01-B07)
    - 🔒 OWASP LLM Top 10 Compliant
    - 🚀 High-speed processing (< 10 seconds)
    
    ## Supported Form Types
    - **B01 (HL0000050)**: Receipt-Bill (ใบเสร็จรับเงิน/ใบแจ้งหนี้)
    - **B04 (HL0000052)**: Invoice (ใบแจ้งหนี้)
    - **B05 (HL0000053)**: Detail (ใบแจ้งรายละเอียดค่ารักษาพยาบาล)
    - **B06 (HL0000054)**: Estimate (ใบประเมินค่าใช้จ่าย/GOP)
    - **B07 (HL0000055)**: Statement (สรุปค่ารักษา)
    
    ## Security
    - 🔐 JWT-like Token Authentication
    - 🛡️ Prompt Injection Protection
    - 🚦 Rate Limiting (60 req/min, 1000 req/hour)
    - 📝 Comprehensive Security Logging
    
    ## Quick Start
    1. Get token from `/auth/login`
    2. Upload image to `/extract/image` or send text to `/extract/text`
    3. Get classification from `/classify`
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware with security restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],  # Restrict origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Restrict methods
    allow_headers=["Content-Type", "Authorization"],  # Restrict headers
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Special handling for Swagger UI/OpenAPI docs
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        # Disable CSP for documentation pages to allow Swagger UI
        # In production, you may want to host Swagger UI locally
        pass  # No CSP headers for docs
    else:
        # Strict CSP for all other endpoints
        security_headers = SecurityHeaders.get_security_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
    
    return response

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware"""
    client_ip = request.client.host
    
    # Skip rate limiting for health checks
    if request.url.path == "/health":
        return await call_next(request)
    
    is_allowed, error_msg = rate_limiter.is_allowed(client_ip)
    if not is_allowed:
        SecurityLogger.log_attack_attempt(
            "RATE_LIMIT_EXCEEDED",
            client_ip,
            {"path": str(request.url.path)}
        )
        return JSONResponse(
            status_code=429,
            content={"error": error_msg, "retry_after": 60}
        )
    
    return await call_next(request)

# Initialize pipeline, classifier, and security
pipeline = None
ai_extractor = None
classifier = None
auth_manager = None
ocr_adapter = None
rate_limiter = RateLimiter()

# Helper functions for parallel processing
def has_multiple_receipts(ocr_text: str) -> bool:
    """ตรวจสอบว่า OCR text มีหลาย receipts หรือไม่"""
    return ocr_text.count('หน้าที่') >= 4  # มีอย่างน้อย 4 หน้า (2 receipts)

def combine_ocr_texts(ocr_texts: List[str]) -> str:
    """รวม ocr_texts เป็น single text สำหรับ parallel processing"""
    return '\n'.join(ocr_texts)

async def process_parallel_extraction(ocr_text: str, form_id: str) -> Dict[str, Any]:
    """Process OCR text with parallel extraction if multiple receipts detected"""
    logger.info("🔍 Checking for multiple receipts in OCR text...")

    if not has_multiple_receipts(ocr_text):
        logger.info("📄 Single receipt detected, using sequential processing")
        return None  # Return None to use sequential processing

    logger.info("📋 Multiple receipts detected, using parallel processing")

    try:
        # Split receipts
        splitter = ReceiptSplitter()
        receipts = splitter.split_by_page_markers(ocr_text)
        logger.info(f"📋 Split into {len(receipts)} receipts")

        if len(receipts) <= 1:
            logger.info("📄 Only 1 receipt after splitting, using sequential processing")
            return None

        # Parallel extraction (batch processing)
        extractor = BatchReceiptExtractor(config)
        # Pass form_id to extract_batch
        results = await asyncio.get_event_loop().run_in_executor(
            None, 
            lambda: extractor.extract_batch(receipts, form_id)
        )

        logger.info(f"✅ Parallel extraction completed: {len(results)} receipts")

        # Format results for API response using JSONFormatter
        formatted_results = []
        total_amount = 0
        total_items = 0

        # Get template config for formatting
        template_config = None
        try:
            if pipeline and hasattr(pipeline, 'template_manager'):
                template_config = pipeline.template_manager.get_template(form_id)
        except Exception as e:
            logger.warning(f"Failed to load template config for formatting: {e}")

        for result in results:
            if result.get('success'):
                raw_data = result.get('data', {})
                
                # Format data using JSONFormatter to match Template_json structure
                try:
                    metadata = {
                        "source_length": 1,
                        "processing_time": result.get('extraction_time', 0),
                        "detected_language": "th",
                        "entities_found": [],
                        "form_id": template_config.get('form_id') if template_config else form_id,
                        "document_type": template_config.get('document_type') if template_config else form_id
                    }
                    
                    # Format using JSONFormatter
                    formatted_data = pipeline.json_formatter.format_to_medical_receipt_json(
                        raw_data,
                        metadata,
                        template_config=template_config
                    )
                    
                    # Attach summary
                    try:
                        if isinstance(formatted_data, dict):
                            formatted_data['summary'] = build_simple_summary(formatted_data)
                    except Exception:
                        pass
                    
                except Exception as e:
                    logger.error(f"❌ Failed to format receipt {result.get('receipt_id')}: {e}", exc_info=True)
                    # Fallback to raw data if formatting fails
                    formatted_data = raw_data
                
                formatted_results.append({
                    'receipt_id': result.get('receipt_id', ''),
                    'receipt_number': result.get('receipt_number', ''),
                    'success': True,
                    'data': formatted_data,
                    'gross_amount': raw_data.get('gross_amount', '0'),
                    'billing_items_count': len(raw_data.get('billing_items', []))
                })

                # Calculate totals
                try:
                    amount_str = raw_data.get('gross_amount', '0').replace(',', '')
                    total_amount += float(amount_str)
                except:
                    pass

                total_items += len(raw_data.get('billing_items', []))
            else:
                formatted_results.append({
                    'receipt_id': result.get('receipt_id', ''),
                    'receipt_number': result.get('receipt_number', ''),
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })

        return {
            'is_parallel': True,
            'total_receipts': len(receipts),
            'successful_receipts': len([r for r in formatted_results if r['success']]),
            'total_amount': f"{total_amount:,.2f}",
            'total_billing_items': total_items,
            'receipts': formatted_results,
            'processing_method': 'parallel_batch'
        }

    except Exception as e:
        logger.error(f"❌ Parallel extraction failed: {e}", exc_info=True)
        return None  # Fallback to sequential processing


"""Startup handled via FastAPI lifespan; deprecated on_event removed."""


# Request/Response Models
class OCRTextInput(BaseModel):
    """
    Input model for OCR text extraction
    
    Supports both 'ocr_texts' and 'texts' field names for backward compatibility
    
    form_id: Form ID (e.g., 'HL0000050', 'HL0000052', 'HL0000053', 'HL0000054', 'HL0000055')
    """
    ocr_texts: Optional[List[str]] = None  # Primary field name
    texts: Optional[List[str]] = None  # Alias for backward compatibility
    form_id: str = "HL0000050"  # Default to HL0000050 (Receipt-Bill)
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('ocr_texts', 'texts', pre=True, always=True)
    def convert_string_to_list(cls, v):
        """Convert string to list if needed"""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]  # Convert single string to list with one element
        elif isinstance(v, list):
            return v  # Already a list, return as-is
        else:
            raise ValueError(f"Field must be a string or list, got {type(v)}")
    
    def __init__(self, **data):
        """Initialize and normalize field names"""
        # If 'texts' is provided but 'ocr_texts' is not, use 'texts' as 'ocr_texts'
        if 'texts' in data and 'ocr_texts' not in data:
            data['ocr_texts'] = data.pop('texts')
        elif 'texts' in data and 'ocr_texts' in data:
            # If both are provided, prefer 'ocr_texts'
            data.pop('texts')
        
        super().__init__(**data)
    
    @validator('ocr_texts', always=True)
    def validate_ocr_texts(cls, v):
        """Ensure ocr_texts is provided"""
        if v is None or len(v) == 0:
            raise ValueError("ocr_texts (or texts) is required and cannot be empty")
        return v
    
    class Config:
        # Allow extra fields to be ignored instead of causing 422
        extra = "ignore"


class ImageExtractionRequest(BaseModel):
    """
    Input model for image extraction with Form ID
    
    form_id: Form ID (e.g., 'HL0000050', 'HL0000052', 'HL0000053', 'HL0000054', 'HL0000055')
    """
    form_id: str = "HL0000050"  # Default to HL0000050 (Receipt-Bill)
    metadata: Optional[Dict[str, Any]] = None


class ExtractionResponse(BaseModel):
    """Response model for extraction results"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timing: Optional[Dict[str, Any]] = None  # processing_method: 0.0=sequential, 1.0=parallel
    request_id: Optional[str] = None


class ClassificationInput(BaseModel):
    """Input model for document classification"""
    texts: List[str]
    metadata: Optional[Dict[str, Any]] = None


class ImageClassificationInput(BaseModel):
    """Input model for document classification from image files"""
    metadata: Optional[Dict[str, Any]] = None


class ClassificationResponse(BaseModel):
    """Response model for classification results"""
    success: bool
    documents: Optional[List[Dict[str, str]]] = None
    classification: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    request_id: Optional[str] = None


class AuthRequest(BaseModel):
    """Authentication request model"""
    username: str
    password: str


class AuthResponse(BaseModel):
    """Authentication response model"""
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None
    expires_in: Optional[int] = None


# Security decorators
def require_auth(required_permission: str = "read"):
    """Decorator to require authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            if not request:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check for Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Invalid authentication header")
            
            token = auth_header.split(" ", 1)[1]
            
            # Validate token
            is_valid, token_data = auth_manager.validate_token(token)
            if not is_valid:
                SecurityLogger.log_attack_attempt(
                    "INVALID_TOKEN",
                    request.client.host,
                    {"token": token[:10] + "..."}
                )
                raise HTTPException(status_code=401, detail="Invalid token")
            
            # Check permission
            if not auth_manager.has_permission(token_data, required_permission):
                SecurityLogger.log_attack_attempt(
                    "INSUFFICIENT_PERMISSIONS",
                    request.client.host,
                    {"user_id": token_data.get("user_id"), "required": required_permission}
                )
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def validate_input_security(input_data: Any, input_type: str = "general"):
    """Validate input for security threats"""
    if hasattr(input_data, 'ocr_texts'):
        # OCR text input
        for text in input_data.ocr_texts:
            is_valid, error = SecurityValidator.validate_input(text, input_type)
            if not is_valid:
                SecurityLogger.log_attack_attempt(
                    "INVALID_INPUT",
                    "unknown",
                    {"input_type": input_type, "error": error, "text_preview": text[:100]}
                )
                raise HTTPException(status_code=403, detail=f"Security validation failed: {error}")
    
    elif hasattr(input_data, 'texts'):
        # Classification input
        for text in input_data.texts:
            is_valid, error = SecurityValidator.validate_input(text, input_type)
            if not is_valid:
                SecurityLogger.log_attack_attempt(
                    "INVALID_INPUT",
                    "unknown",
                    {"input_type": input_type, "error": error, "text_preview": text[:100]}
                )
                raise HTTPException(status_code=403, detail=f"Security validation failed: {error}")
    
    # Check for prompt injection
    if hasattr(input_data, 'ocr_texts'):
        combined_text = ' '.join(input_data.ocr_texts)
    elif hasattr(input_data, 'texts'):
        combined_text = ' '.join(input_data.texts)
    else:
        return
    
    is_injection, patterns = PromptInjectionDetector.detect_prompt_injection(combined_text)
    if is_injection:
        injection_score = PromptInjectionDetector.get_injection_score(combined_text)
        # Allow low-risk OCR-specific patterns (punctuation/repetition) to pass, but keep logs
        low_risk_patterns = {"EXCESSIVE_PUNCTUATION", "SUSPICIOUS_REPETITION"}
        non_low_risk = [p for p in patterns if p not in low_risk_patterns]
        if non_low_risk and injection_score >= 0.2:
            SecurityLogger.log_attack_attempt(
                "PROMPT_INJECTION_ATTEMPT",
                "unknown",
                {
                    "patterns": patterns,
                    "score": injection_score,
                    "text_preview": combined_text[:200]
                }
            )
            raise HTTPException(
                status_code=403, 
                detail=f"Security validation failed: Potential prompt injection detected (risk score: {injection_score:.2f})"
            )
        else:
            # Log and continue for low-risk OCR noise
            logger.warning(f"[OWASP LLM01] Allowing low-risk OCR input despite patterns={patterns}, score={injection_score:.2f}")


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint - API information"""
    # Build dynamic supported_form_ids from Template API (with safe fallback)
    supported_form_ids = {}
    source = "api"
    try:
        if pipeline and hasattr(pipeline, 'template_manager'):
            all_templates = pipeline.template_manager.get_all_templates()
            for t in all_templates:
                form_id = t.get('form_id')
                doc_en = t.get('document_type')
                doc_th = t.get('document_type_thai')
                if form_id and (doc_en or doc_th):
                    label = doc_en if doc_th is None else f"{doc_en} ({doc_th})"
                    supported_form_ids[form_id] = label
            supported_form_ids["note"] = "Use Form ID directly in 'form_id' parameter"
        else:
            raise RuntimeError("Template manager not initialized")
    except Exception as e:
        logger.warning(f"Using static supported_form_ids fallback: {e}")
        source = "fallback"
        supported_form_ids = {
            "HL0000050": "Receipt-Bill (ใบเสร็จรับเงิน/ใบแจ้งหนี้)",
            "HL0000052": "Invoice (ใบแจ้งหนี้)",
            "HL0000053": "Detail (ใบแจ้งรายละเอียดค่ารักษาพยาบาล)",
            "HL0000054": "Estimate (ใบประเมินค่าใช้จ่าย/GOP)",
            "HL0000055": "Statement (สรุปค่ารักษา)",
            "note": "Use Form ID directly in 'form_id' parameter"
        }

    return {
        "name": "Medical Receipt Extraction API",
        "version": "1.0.0",
        "status": "running",
        "        endpoints": {
            "POST /extract/image": "Extract from image file (supports template parameter)",
            "POST /extract/text": "Extract from OCR text (AUTO parallel processing for multiple receipts)",
            "POST /classify": "Classify document type from text (HYBRID: weight-based + AI validation)",
            "POST /classify/image": "Classify document type from image file (OCR + HYBRID classification)",
            "GET /health": "Health check",
            "GET /stats": "API statistics"
        },
        "supported_form_ids": supported_form_ids,
        "supported_form_ids_source": source,
        "supported_document_types": {
            "Medical Receipt": "CM0000095",
            "Receipt": "CM0000096", 
            "Others": "CM0000097"
        },
        "processing_features": {
            "parallel_processing": "AUTO (detects multiple receipts and processes in parallel)",
            "batch_processing": "enabled for large documents",
            "hybrid_classification": "weight-based + AI validation for maximum accuracy",
            "template_api": "dynamic form configuration",
            "performance": "15-30x faster for multiple receipts, smart AI usage"
        },
        "security_features": {
            "rate_limiting": "enabled",
            "input_validation": "enabled",
            "prompt_injection_protection": "enabled",
            "authentication": "optional",
            "security_headers": "enabled"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "pipeline": "initialized" if pipeline else "not initialized",
        "classifier": "initialized" if classifier else "not initialized",
        "security": "enabled"
    }


@app.post("/auth/login", response_model=AuthResponse)
async def login(auth_data: AuthRequest):
    """
    Authentication endpoint (demo implementation)
    In production, use proper user database and password hashing
    """
    # Demo credentials (in production, use proper authentication)
    demo_users = {
        "admin": {"password": "admin123", "permissions": ["read", "write", "admin"]},
        "user": {"password": "user123", "permissions": ["read"]},
        "demo": {"password": "demo123", "permissions": ["read"]}
    }
    
    if auth_data.username in demo_users:
        user = demo_users[auth_data.username]
        if auth_data.password == user["password"]:
            token = auth_manager.generate_token(
                auth_data.username, 
                user["permissions"]
            )
            
            SecurityLogger.log_security_event(
                "USER_LOGIN_SUCCESS",
                {"username": auth_data.username},
                "INFO"
            )
            
            return AuthResponse(
                success=True,
                token=token,
                expires_in=3600
            )
    
    SecurityLogger.log_attack_attempt(
        "INVALID_LOGIN",
        "unknown",
        {"username": auth_data.username}
    )
    
    return AuthResponse(
        success=False,
        error="Invalid credentials"
    )


@app.post("/extract/image", response_model=ExtractionResponse)
async def extract_from_image(file: UploadFile = File(...), form_id: str = "HL0000050"):
    """
    Extract medical receipt data from image file
    
    Args:
        file: Image file (PNG, JPG, JPEG)
        form_id: Form ID (e.g., 'HL0000050', 'HL0000052', 'HL0000053', 'HL0000054', 'HL0000055')
    
    Returns:
        ExtractionResponse with extracted data
    
    Example:
        form_id='HL0000050' for Receipt-Bill
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Security validation
    is_valid, error_msg = SecurityValidator.validate_file_upload(
        file.filename, file.content_type, file.size
    )
    if not is_valid:
        SecurityLogger.log_attack_attempt(
            "INVALID_FILE_UPLOAD",
            "unknown",
            {"filename": file.filename, "content_type": file.content_type}
        )
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save uploaded file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        logger.info(f"Processing image: {file.filename} with Form ID: {form_id}")
        
        # Step 1: Load template from API using Form ID
        template_config = pipeline.template_manager.get_template(form_id)
        if template_config:
            logger.info(f"Template loaded: {template_config.get('document_type')} (Form ID: {template_config.get('form_id')})")
        else:
            logger.warning(f"Template for Form ID '{form_id}' not found, using default")
        
        # Step 2: Process with pipeline using Form ID
        result = pipeline.process_document(tmp_path, template=form_id)
        
        # Clean up
        os.unlink(tmp_path)
        
        if result['success']:
            # Attach simple summary
            data_obj = result['data']
            try:
                if isinstance(data_obj, dict):
                    data_obj['summary'] = build_simple_summary(data_obj)
            except Exception:
                pass

            resp = ExtractionResponse(
                success=True,
                data=data_obj,
                timing=result.get('timing'),
                request_id=result['data'].get('metadata', {}).get('document_id')
            )
            # Save API response for mapping verification
            save_api_response(
                endpoint='/extract/image',
                request_id=resp.request_id or str(uuid.uuid4()),
                response_obj=resp.dict(),
                request_meta={'form_id': form_id, 'filename': file.filename}
            )
            return resp
        else:
            resp = ExtractionResponse(
                success=False,
                error=result.get('error', 'Unknown error')
            )
            save_api_response(
                endpoint='/extract/image',
                request_id=str(uuid.uuid4()),
                response_obj=resp.dict(),
                request_meta={'form_id': form_id, 'filename': file.filename}
            )
            return resp
    
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/text", response_model=ExtractionResponse)
async def extract_from_text(request: Request, input_data: OCRTextInput = Body(...)):
    """
    Extract medical receipt data from OCR text
    
    Args:
        request: FastAPI Request object (for logging client IP)
        input_data: OCRTextInput with list of OCR texts and Form ID
    
    Returns:
        ExtractionResponse with extracted data
    
    Example:
        {
            "ocr_texts": ["text1", "text2"],
            "form_id": "HL0000052"
        }
        OR
        {
            "ocr_texts": "single text",
            "form_id": "HL0000052"
        }
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"📥 Received request from {client_ip}: ocr_texts={len(input_data.ocr_texts) if input_data.ocr_texts else 0} items, form_id={input_data.form_id}")
    
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    # Validate required fields
    if not input_data.ocr_texts or len(input_data.ocr_texts) == 0:
        raise HTTPException(
            status_code=422, 
            detail="ocr_texts is required and cannot be empty"
        )
    
    # Validate form_id format (should start with HL or NO)
    if input_data.form_id and not (input_data.form_id.startswith('HL') or input_data.form_id.startswith('NO')):
        logger.warning(f"⚠️ Invalid form_id format: {input_data.form_id}, using default")
        input_data.form_id = "HL0000050"
    
    # Security validation
    try:
        validate_input_security(input_data, "prompt")
    except HTTPException as e:
        # Re-raise security exceptions as-is (they use 403)
        raise e
    
    try:
        logger.info(f"Processing {len(input_data.ocr_texts)} OCR texts with Form ID: {input_data.form_id}")

        # Step 1: Load template from API using Form ID
        template_config = pipeline.template_manager.get_template(input_data.form_id)
        if template_config:
            logger.info(f"Template loaded: {template_config.get('document_type')} (Form ID: {template_config.get('form_id')})")
        else:
            logger.warning(f"Template for Form ID '{input_data.form_id}' not found, using default")

        # Step 2: Convert OCR texts to format expected by pipeline
        ocr_results = []
        for i, text in enumerate(input_data.ocr_texts):
            ocr_results.append({
                'text': text,
                'confidence': 0.95,
                'bbox': [[0, i*20], [len(text)*10, i*20], [len(text)*10, (i+1)*20], [0, (i+1)*20]],
                'position': {'x': 0, 'y': i*20, 'width': len(text)*10, 'height': 20}
            })

        # Step 3: Extract using AI - AI will extract data by JSON keys matching template
        logger.info("📤 Sending OCR text to AI API for extraction...")
        simple_data = pipeline.simple_extractor.extract_simple(ocr_results, save_request=True, template=input_data.form_id)
        logger.info(f"✅ AI extraction completed: {len(simple_data.get('billing_items', []))} billing items extracted")

        # Step 4: Map extracted keys to template_json structure
        logger.info("🔄 Mapping extracted keys to template_json structure...")
        metadata = {
            "source_length": len(ocr_results),
            "processing_time": 0,
            "detected_language": "th",
            "entities_found": [],
            "form_id": template_config.get('form_id') if template_config else input_data.form_id,
            "document_type": template_config.get('document_type') if template_config else input_data.form_id
        }

        formatted_json = pipeline.json_formatter.format_to_medical_receipt_json(
            simple_data,
            metadata,
            template_config=template_config
        )
        logger.info("✅ JSON formatting completed")

        # Attach simple summary
        try:
            if isinstance(formatted_json, dict):
                formatted_json['summary'] = build_simple_summary(formatted_json)
        except Exception:
            pass

        resp = ExtractionResponse(
            success=True,
            data=formatted_json,
            timing={'processing_method': 0.0, 'ai_extraction_time': 0.0},
            request_id=str(uuid.uuid4())
        )
        save_api_response(
            endpoint='/extract/text',
            request_id=resp.request_id,
            response_obj=resp.dict(),
            request_meta={'form_id': input_data.form_id, 'ocr_texts_count': len(input_data.ocr_texts), 'mode': 'simplified'}
        )
        return resp
    
    except Exception as e:
        logger.error(f"Error processing text: {e}", exc_info=True)
        resp = ExtractionResponse(
            success=False,
            error=str(e)
        )
        save_api_response(
            endpoint='/extract/text',
            request_id=str(uuid.uuid4()),
            response_obj=resp.dict(),
            request_meta={'form_id': input_data.form_id, 'ocr_texts_count': len(input_data.ocr_texts), 'mode': 'error'}
        )
        return resp


@app.post("/v2/extract/text")
async def extract_text_v2(input_data: OCRTextInput = Body(...)):
    """
    Raw AI Extraction V2
    
    Sends raw OCR text to AI and returns the raw content string.
    No parsing, no formatting, just pure AI response.
    
    Args:
        input_data: OCRTextInput with list of OCR texts and Form ID
        
    Returns:
        Dictionary containing raw AI content
    """
    if not ai_extractor:
        raise HTTPException(status_code=503, detail="AI Extractor V2 not initialized")
        
    # Validate inputs
    if not input_data.ocr_texts:
        raise HTTPException(status_code=422, detail="ocr_texts is required")
        
    # Combine OCR texts
    combined_text = "\n".join(input_data.ocr_texts)
    
    try:
        logger.info(f"📤 Sending raw text to AI V2 (length: {len(combined_text)}) with form_id: {input_data.form_id}")
        content, usage = await ai_extractor.extract(combined_text, form_id=input_data.form_id)
        
        if content:
            return {
                "success": True,
                "data": content,
                "token_usage": usage,
                "request_id": str(uuid.uuid4())
            }
        else:
            return {
                "success": False,
                "error": "AI returned empty response"
            }
            
    except Exception as e:
        logger.error(f"Error in V2 extraction: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/classify", response_model=ClassificationResponse)
async def classify_document(input_data: ClassificationInput):
    """
    Classify document type from OCR text using Hybrid Classification System

    Combines weight-based scoring with AI validation for maximum accuracy:
    - Fast weight-based classification using advanced keyword matching
    - AI validation when confidence is below threshold
    - Weighted combination of both results for optimal accuracy

    Supports 5 Form IDs: HL0000050, HL0000052, HL0000053, HL0000054, HL0000055

    Args:
        input_data: ClassificationInput with list of text strings

    Returns:
        ClassificationResponse with document type classification:
        - HL0000050: Receipt-Bill (ใบเสร็จรับเงิน/ใบแจ้งหนี้)
        - HL0000052: Invoice (ใบแจ้งหนี้)
        - HL0000053: Detail (ใบแจ้งรายละเอียดค่ารักษาพยาบาล)
        - HL0000054: Estimate (ใบประเมินค่าใช้จ่าย/ใบการันตี/ใบสรุปค่าใช้จ่าย)
        - HL0000055: Statement (Statement รพ.)
    """
    if not classifier:
        raise HTTPException(status_code=503, detail="Classifier not initialized")
    
    # Security validation
    validate_input_security(input_data, "general")
    
    try:
        logger.info(f"Classifying document from {len(input_data.texts)} text lines")
        
        # Classify documents
        result = classifier.classify_documents(input_data.texts, save_request=True)
        
        if result['success']:
            return ClassificationResponse(
                success=True,
                documents=result['documents'],
                classification=result.get('classification'),
                request_id=str(uuid.uuid4())
            )
        else:
            return ClassificationResponse(
                success=False,
                error="Classification failed"
            )
    
    except Exception as e:
        logger.error(f"Error classifying document: {e}", exc_info=True)
        return ClassificationResponse(
            success=False,
            error=str(e)
        )


@app.post("/classify/image", response_model=ClassificationResponse)

# Catch-all route for handling unwanted requests (routers, bots, etc.)
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"], operation_id="catch_all_handler")
async def catch_all_handler(request: Request, path: str):
    """
    Handle unwanted requests that are commonly made by:
    - Network devices looking for router interfaces
    - UPnP discovery services
    - Web crawlers and bots
    - Misconfigured applications
    """
    client_ip = request.client.host
    user_agent = request.headers.get("User-Agent", "")

    # Log suspicious requests for monitoring
    suspicious_paths = [
        "/loginMsg.js", "/cgi/get.cgi", "/WFADeviceDesc.xml",
        "/setup.cgi", "/index.html", "/login.html", "/admin.html",
        "/router", "/modem", "/gateway"
    ]

    # Check if this is a suspicious request
    is_suspicious = any(suspicious in path.lower() for suspicious in suspicious_paths)

    if is_suspicious:
        SecurityLogger.log_attack_attempt(
            "UNWANTED_REQUEST",
            client_ip,
            {
                "path": path,
                "method": request.method,
                "user_agent": user_agent[:200],  # Truncate long UAs
                "headers": dict(request.headers)
            }
        )

        logger.info(f"🚫 Blocked suspicious request from {client_ip}: {request.method} {path}")

    # Return clean 404 for all unknown paths
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found on this server.",
            "timestamp": datetime.now().isoformat()
        }
    )
async def classify_document_from_image(
    file: UploadFile = File(...),
    metadata: Optional[str] = None
):
    """
    Classify document type from image file using OCR + Hybrid Classification

    This endpoint:
    1. Receives image file (PNG, JPG, JPEG, BMP, TIFF)
    2. Performs OCR to extract text from image
    3. Uses Hybrid Classification to determine document type
    4. Returns classification results with OCR text

    Supports 5 Form IDs: HL0000050, HL0000052, HL0000053, HL0000054, HL0000055

    Args:
        file: Image file to classify
        metadata: Optional JSON metadata string

    Returns:
        ClassificationResponse with document type classification and OCR text
    """
    if not ocr_adapter:
        raise HTTPException(status_code=503, detail="OCR Adapter not initialized")

    if not classifier:
        raise HTTPException(status_code=503, detail="Classifier not initialized")

    # Validate file type
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Parse metadata
    parsed_metadata = None
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            logger.warning(f"Invalid metadata JSON: {metadata}")

    try:
        logger.info(f"Processing image for classification: {file.filename}")

        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Step 1: OCR - Extract text from image
            logger.info("Step 1: Performing OCR on image")
            ocr_result = ocr_adapter.extract_text(tmp_path)

            if not ocr_result or not ocr_result.get('success'):
                error_msg = ocr_result.get('error', 'OCR failed') if ocr_result else 'OCR failed'
                raise HTTPException(status_code=422, detail=f"OCR extraction failed: {error_msg}")

            ocr_text = ocr_result.get('text', '').strip()
            if not ocr_text:
                raise HTTPException(status_code=422, detail="No text extracted from image")

            ocr_lines = ocr_text.split('\n')
            logger.info(f"OCR successful: {len(ocr_lines)} lines extracted")

            # Step 2: Classify using extracted text
            logger.info("Step 2: Classifying document from OCR text")
            classification_result = classifier.classify_documents(ocr_lines, save_request=True)

            if classification_result['success']:
                # Add OCR information to response
                response_data = {
                    'success': True,
                    'documents': classification_result['documents'],
                    'classification': classification_result.get('classification'),
                    'ocr_info': {
                        'text_length': len(ocr_text),
                        'line_count': len(ocr_lines),
                        'engine_used': ocr_result.get('engine', 'unknown')
                    },
                    'request_id': str(uuid.uuid4())
                }

                # Include OCR text in response if requested
                if parsed_metadata and parsed_metadata.get('include_ocr_text', False):
                    response_data['ocr_text'] = ocr_text[:5000]  # Limit text length

                logger.info(f"✅ Image classification completed: {classification_result['documents'][0].get('form_id', 'unknown')}")
                return ClassificationResponse(**response_data)
            else:
                return ClassificationResponse(
                    success=False,
                    error="Classification failed after OCR",
                    request_id=str(uuid.uuid4())
                )

        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in image classification: {e}", exc_info=True)
        return ClassificationResponse(
            success=False,
            error=str(e),
            request_id=str(uuid.uuid4())
        )


@app.post("/extract/batch")
async def extract_batch(files: List[UploadFile] = File(...)):
    """
    Extract medical receipt data from multiple images
    
    Args:
        files: List of image files
    
    Returns:
        List of extraction results
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")
    
    results = []
    
    for file in files:
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            logger.info(f"Processing image: {file.filename}")
            
            # Process with pipeline
            result = pipeline.process_document(tmp_path)
            
            # Clean up
            os.unlink(tmp_path)
            
            results.append({
                'filename': file.filename,
                'success': result['success'],
                'data': result.get('data') if result['success'] else None,
                'error': result.get('error') if not result['success'] else None
            })
        
        except Exception as e:
            logger.error(f"Error processing {file.filename}: {e}")
            results.append({
                'filename': file.filename,
                'success': False,
                'error': str(e)
            })
    
    return {
        'total': len(files),
        'successful': sum(1 for r in results if r['success']),
        'failed': sum(1 for r in results if not r['success']),
        'results': results
    }


@app.get("/stats")
@require_auth(["read"])
async def get_statistics(request: Request):
    """Get API statistics (requires authentication)"""
    if not pipeline:
        return {"error": "Pipeline not initialized"}
    
    stats = pipeline.get_statistics() if hasattr(pipeline, 'get_statistics') else {}
    
    # Add template manager stats if available
    template_stats = {}
    if hasattr(pipeline, 'template_manager'):
        try:
            template_stats = pipeline.template_manager.get_statistics()
        except:
            pass
    
    return {
        "pipeline_stats": stats,
        "template_stats": template_stats,
        "api_info": {
            "version": "2.0.0",
            "model": "qwen/qwen3-4b-2507",
            "method": "Two-Step AI Extraction",
            "template_api": "active" if template_stats else "inactive"
        }
    }


@app.get("/templates/form-ids")
async def list_form_ids():
    """
    List all available Form IDs from API
    
    Returns:
        List of Form IDs with their metadata
    """
    if not pipeline or not hasattr(pipeline, 'template_manager'):
        raise HTTPException(status_code=503, detail="Template manager not initialized")
    
    try:
        # Get all templates
        all_templates = pipeline.template_manager.get_all_templates()
        
        form_ids = []
        for template in all_templates:
            form_ids.append({
                "form_id": template.get('form_id'),
                "document_type": template.get('document_type'),
                "document_type_thai": template.get('document_type_thai'),
                "description": template.get('description'),
                "category": template.get('category')
            })
        
        return {
            "success": True,
            "form_ids": form_ids,
            "total": len(form_ids),
            "note": "Use 'form_id' directly in API requests",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error listing form IDs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/{form_id}/structure")
async def get_template_structure(form_id: str):
    """
    Get Template_json structure for a specific Form ID
    
    Useful for analyzing template structure before extraction
    
    Args:
        form_id: Form ID (e.g., 'HL0000050', 'HL0000052')
    
    Returns:
        Complete template structure including Template_json
    """
    if not pipeline or not hasattr(pipeline, 'template_manager'):
        raise HTTPException(status_code=503, detail="Template manager not initialized")
    
    try:
        # Get template from API
        template = pipeline.template_manager.get_template(form_id)
        
        if not template:
            raise HTTPException(
                status_code=404,
                detail=f"Template not found for Form ID: {form_id}. Use /templates/form-ids to see available Form IDs."
            )
        
        # Extract template structure
        template_structure = template.get('template_structure', {})
        
        # Extract document_info fields for easy reference
        document_info_fields = []
        if 'documents' in template_structure and len(template_structure['documents']) > 0:
            doc_info = template_structure['documents'][0].get('document_info', [])
            for field in doc_info:
                field_info = {
                    'code': field.get('code'),
                    'type': field.get('type'),
                    'description': f"Field: {field.get('code')} ({field.get('type')})"
                }
                
                # If it's billing_items or order_items, show structure
                if field.get('code') in ['billing_items', 'order_items']:
                    template_value = field.get('value', [])
                    if template_value and len(template_value) > 0:
                        template_item = template_value[0]
                        if isinstance(template_item, dict) and 'value' in template_item:
                            field_info['structure'] = [
                                f.get('code') for f in template_item.get('value', []) if isinstance(f, dict)
                            ]
                
                document_info_fields.append(field_info)
        
        return {
            "success": True,
            "form_id": template.get('form_id'),
            "document_type": template.get('document_type'),
            "document_type_thai": template.get('document_type_thai'),
            "description": template.get('description'),
            "template_structure": template_structure,
            "document_info_fields": document_info_fields,
            "metadata": template.get('metadata', {}),
            "note": "This is the exact structure used for JSON output formatting",
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template structure for {form_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/stats")
async def template_statistics():
    """
    Get template manager statistics
    
    Returns:
        Statistics about template usage and cache
    """
    if not pipeline or not hasattr(pipeline, 'template_manager'):
        raise HTTPException(status_code=503, detail="Template manager not initialized")
    
    try:
        stats = pipeline.template_manager.get_statistics()
        
        return {
            "success": True,
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting template stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/templates/refresh")
async def refresh_templates():
    """
    Refresh template cache
    
    Useful after templates are updated on the server
    """
    if not pipeline or not hasattr(pipeline, 'template_manager'):
        raise HTTPException(status_code=503, detail="Template manager not initialized")
    
    try:
        pipeline.template_manager.refresh_cache()
        
        return {
            "success": True,
            "message": "Template cache refreshed",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error refreshing templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle FastAPI validation errors (422 Unprocessable Content)
    Logs detailed validation errors for debugging
    """
    client_ip = request.client.host if request.client else "unknown"
    errors = exc.errors()
    
    # Log validation errors with details
    logger.error(
        f"❌ Validation Error (422) from {client_ip}: {request.url.path}\n"
        f"   Errors: {json.dumps(errors, indent=2, ensure_ascii=False)}"
    )
    
    # Build detailed error message
    error_details = []
    for error in errors:
        field = " -> ".join(str(loc) for loc in error.get("loc", []))
        error_type = error.get("type", "unknown")
        error_msg = error.get("msg", "Validation error")
        error_details.append({
            "field": field,
            "type": error_type,
            "message": error_msg
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "message": "Request body validation failed",
            "details": error_details,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found on this server.",
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


# Main
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Medical Receipt Extraction API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8888, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Medical Receipt Extraction API Server")
    print("=" * 80)
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Docs: http://{args.host}:{args.port}/docs")
    print("=" * 80)
    
    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )

