"""
Security Module for OWASP Top 10 for LLM Applications Compliance
ป้องกันช่องโหว่ความปลอดภัยตามมาตรฐาน OWASP
"""

import re
import hashlib
import hmac
import time
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta
import secrets
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

# Load security configuration
def load_security_config():
    """Load security settings from config.json"""
    try:
        config_path = Path(__file__).parent / "config.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('security', {})
    except Exception as e:
        logger.warning(f"Failed to load security config: {e}. Using defaults.")
    
    # Default values if config not found
    return {
        'input_validation': {
            'max_input_size': 500000,  # 500KB
            'allow_null_bytes': False
        },
        'prompt_injection': {
            'enabled': True,
            'punctuation_threshold': 0.5,  # 50%
            'repetition_threshold': 0.3,  # 30%
            'log_detections': True
        },
        'rate_limiting': {
            'enabled': True,
            'requests_per_minute': 60,
            'requests_per_hour': 1000
        }
    }

SECURITY_CONFIG = load_security_config()
"""
Allow turning off the entire security module via config.
If `security.enabled` is set to false, validation, rate limiting,
and prompt injection detection will be bypassed.
"""


class SecurityValidator:
    """Input validation และ sanitization"""
    
    # Dangerous patterns for prompt injection
    PROMPT_INJECTION_PATTERNS = [
        r'ignore\s+previous\s+instructions',
        r'forget\s+everything',
        r'you\s+are\s+now',
        r'system\s*prompt',
        r'act\s+as\s+if',
        r'pretend\s+to\s+be',
        r'roleplay\s+as',
        r'new\s+instructions',
        r'override\s+previous',
        r'bypass\s+security',
        r'admin\s+access',
        r'root\s+privileges',
        r'<script.*?>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'data:text/html',
        r'vbscript:',
        r'<iframe.*?>.*?</iframe>',
        r'<object.*?>.*?</object>',
        r'<embed.*?>.*?</embed>',
        r'<link.*?>.*?</link>',
        r'<meta.*?>.*?</meta>',
        r'<style.*?>.*?</style>',
        r'expression\s*\(',
        r'@import',
        r'url\s*\(',
        r'behavior\s*:',
        r'filter\s*:',
        r'-moz-binding',
        r'\\x[0-9a-fA-F]{2}',
        r'\\u[0-9a-fA-F]{4}',
        r'\\[0-7]{1,3}',
    ]
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r'union\s+select',
        r'drop\s+table',
        r'delete\s+from',
        r'insert\s+into',
        r'update\s+set',
        r'exec\s*\(',
        r'execute\s*\(',
        r'sp_',
        r'xp_',
        # SQL comment patterns - only match when it looks like SQL injection
        # Match -- followed by whitespace and text (SQL comment), but not when it's part of decorative text
        r'(?:union|select|drop|delete|insert|update|exec|execute|create|alter|from|where|having|group|order)\s+.*?--\s+\w',  # SQL comment after SQL keywords
        r'/\*.*?\*/',  # SQL comment block
        r';\s*drop',
        r';\s*delete',
        r';\s*insert',
        r';\s*update',
        r';\s*exec',
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',
        r'\.\.\\',
        r'%2e%2e%2f',
        r'%2e%2e%5c',
        r'%252e%252e%252f',
        r'%252e%252e%255c',
    ]
    
    @classmethod
    def validate_input(cls, text: str, input_type: str = "general") -> Tuple[bool, str]:
        """
        Validate input text for security threats
        
        Args:
            text: Input text to validate
            input_type: Type of input (general, prompt, filename, etc.)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Bypass all validations if security module disabled
        if not SECURITY_CONFIG.get('enabled', True):
            return True, ""

        if not isinstance(text, str):
            return False, "Input must be a string"
        
        # Check length (from config)
        max_size = SECURITY_CONFIG.get('input_validation', {}).get('max_input_size', 500000)
        if len(text) > max_size:
            # Format size in KB or MB for error message
            if max_size >= 1000000:
                size_str = f"{max_size // 1000000}MB"
            else:
                size_str = f"{max_size // 1000}KB"
            return False, f"Input too long (max {size_str})"
        
        # Check for null bytes (from config)
        allow_null = SECURITY_CONFIG.get('input_validation', {}).get('allow_null_bytes', False)
        if not allow_null and '\x00' in text:
            return False, "Null bytes not allowed"
        
        # Check for prompt injection
        if input_type in ["prompt", "general"]:
            for pattern in cls.PROMPT_INJECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.warning(f"[OWASP LLM01: Prompt Injection] Detected pattern: {pattern}")
                    return False, f"Potentially malicious input detected"
        
        # Check for SQL injection
        if input_type in ["query", "general"]:
            for pattern in cls.SQL_INJECTION_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.warning(f"[OWASP LLM02: Insecure Output Handling] SQL injection pattern detected: {pattern}")
                    return False, f"Potentially malicious input detected"
        
        # Check for path traversal
        if input_type in ["filename", "path", "general"]:
            for pattern in cls.PATH_TRAVERSAL_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    logger.warning(f"[OWASP LLM03: Training Data Poisoning] Path traversal pattern detected: {pattern}")
                    return False, f"Potentially malicious input detected"
        
        return True, ""
    
    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """
        Sanitize text by removing potentially dangerous content
        
        Args:
            text: Text to sanitize
            
        Returns:
            Sanitized text
        """
        # If security is disabled, return text unchanged
        if not SECURITY_CONFIG.get('enabled', True):
            return text

        if not isinstance(text, str):
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters except newlines and tabs
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        if len(text) > 10000:
            text = text[:10000]
        
        return text
    
    @classmethod
    def validate_file_upload(cls, filename: str, content_type: str, file_size: int) -> Tuple[bool, str]:
        """
        Validate file upload for security
        
        Args:
            filename: Name of uploaded file
            content_type: MIME type of file
            file_size: Size of file in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Bypass validations if security disabled
        if not SECURITY_CONFIG.get('enabled', True):
            return True, ""

        # Check filename
        is_valid, error = cls.validate_input(filename, "filename")
        if not is_valid:
            logger.warning(f"[OWASP LLM03: Training Data Poisoning] Invalid filename detected: {filename}")
            return False, error
        
        # Check file size (10MB limit)
        if file_size > 10 * 1024 * 1024:
            logger.warning(f"[OWASP LLM06: Excessive Agency] File too large: {file_size} bytes")
            return False, "File too large (max 10MB)"
        
        # Check content type
        allowed_types = [
            'image/jpeg',
            'image/png', 
            'image/gif',
            'image/webp',
            'image/bmp',
            'image/tiff'
        ]
        
        if content_type not in allowed_types:
            logger.warning(f"[OWASP LLM03: Training Data Poisoning] Disallowed content type: {content_type}")
            return False, f"File type not allowed: {content_type}"
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            logger.warning(f"[OWASP LLM03: Training Data Poisoning] Disallowed file extension: {file_ext}")
            return False, f"File extension not allowed: {file_ext}"
        
        return True, ""


class RateLimiter:
    """Rate limiting เพื่อป้องกัน DDoS และ abuse"""
    
    def __init__(self):
        self.requests = {}  # {client_id: [timestamps]}
        rl_conf = SECURITY_CONFIG.get('rate_limiting', {})
        self.max_requests_per_minute = rl_conf.get('requests_per_minute', 60)
        self.max_requests_per_hour = rl_conf.get('requests_per_hour', 1000)
        self.enabled = SECURITY_CONFIG.get('enabled', True) and rl_conf.get('enabled', True)
        self.cleanup_interval = 300  # 5 minutes
    
    def is_allowed(self, client_id: str) -> Tuple[bool, str]:
        """
        Check if request is allowed based on rate limiting
        
        Args:
            client_id: Client identifier (IP address or user ID)
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        # If security/rate limiting is disabled, always allow
        if not self.enabled:
            return True, ""

        current_time = time.time()
        
        # Initialize client if not exists
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Clean old requests
        self.requests[client_id] = [
            timestamp for timestamp in self.requests[client_id]
            if current_time - timestamp < 3600  # Keep last hour
        ]
        
        # Check minute limit
        minute_ago = current_time - 60
        recent_requests = [
            timestamp for timestamp in self.requests[client_id]
            if timestamp > minute_ago
        ]
        
        if len(recent_requests) >= self.max_requests_per_minute:
            logger.warning(f"[OWASP LLM06: Excessive Agency & LLM09: Overreliance] Rate limit exceeded for client {client_id} - {len(recent_requests)} requests in last minute")
            return False, "Too many requests per minute"
        
        # Check hour limit
        if len(self.requests[client_id]) >= self.max_requests_per_hour:
            logger.warning(f"[OWASP LLM06: Excessive Agency & LLM09: Overreliance] Hourly rate limit exceeded for client {client_id} - {len(self.requests[client_id])} requests in last hour")
            return False, "Too many requests per hour"
        
        # Add current request
        self.requests[client_id].append(current_time)
        
        return True, ""
    
    def cleanup(self):
        """Clean up old request records"""
        current_time = time.time()
        for client_id in list(self.requests.keys()):
            self.requests[client_id] = [
                timestamp for timestamp in self.requests[client_id]
                if current_time - timestamp < 3600
            ]
            if not self.requests[client_id]:
                del self.requests[client_id]


class AuthenticationManager:
    """Authentication และ authorization management"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode()
        self.tokens = {}  # {token: {user_id, expires_at, permissions}}
        self.token_expiry = 3600  # 1 hour
    
    def generate_token(self, user_id: str, permissions: List[str] = None) -> str:
        """
        Generate authentication token
        
        Args:
            user_id: User identifier
            permissions: List of permissions
            
        Returns:
            JWT-like token
        """
        if permissions is None:
            permissions = ["read"]
        
        expires_at = time.time() + self.token_expiry
        
        token_data = {
            "user_id": user_id,
            "expires_at": expires_at,
            "permissions": permissions,
            "created_at": time.time()
        }
        
        # Create signature
        token_json = json.dumps(token_data, sort_keys=True)
        signature = hmac.new(
            self.secret_key,
            token_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine token data and signature
        token = base64.b64encode(
            f"{token_json}.{signature}".encode()
        ).decode()
        
        self.tokens[token] = token_data
        
        return token
    
    def validate_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate authentication token
        
        Args:
            token: Token to validate
            
        Returns:
            Tuple of (is_valid, token_data)
        """
        try:
            # Decode token
            token_str = base64.b64decode(token.encode()).decode()
            token_json, signature = token_str.rsplit('.', 1)
            
            # Verify signature
            expected_signature = hmac.new(
                self.secret_key,
                token_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning(f"[OWASP LLM08: Excessive Agency] Invalid token signature detected")
                return False, {}
            
            # Parse token data
            token_data = json.loads(token_json)
            
            # Check expiration
            if time.time() > token_data["expires_at"]:
                logger.warning(f"[OWASP LLM08: Excessive Agency] Expired token detected for user: {token_data.get('user_id', 'unknown')}")
                return False, {}
            
            # Check if token exists in our records
            if token not in self.tokens:
                logger.warning(f"[OWASP LLM08: Excessive Agency] Token not found in records")
                return False, {}
            
            return True, token_data
            
        except Exception as e:
            logger.error(f"[OWASP LLM08: Excessive Agency] Token validation error: {e}")
            return False, {}
    
    def has_permission(self, token_data: Dict[str, Any], required_permission: str) -> bool:
        """
        Check if user has required permission
        
        Args:
            token_data: Validated token data
            required_permission: Required permission
            
        Returns:
            True if user has permission
        """
        has_perm = required_permission in token_data.get("permissions", [])
        if not has_perm:
            logger.warning(f"[OWASP LLM08: Excessive Agency] Permission denied for user {token_data.get('user_id', 'unknown')}: required '{required_permission}'")
        return has_perm


class SecurityHeaders:
    """Security headers สำหรับ HTTP responses"""
    
    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get security headers (strict CSP for API endpoints)"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            "X-Permitted-Cross-Domain-Policies": "none"
            # Note: Cross-Origin headers removed for Swagger UI compatibility
        }


class SecurityLogger:
    """Security logging และ monitoring"""
    
    @staticmethod
    def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO", owasp_category: str = None):
        """
        Log security-related events
        
        Args:
            event_type: Type of security event
            details: Event details
            severity: Log severity level
            owasp_category: OWASP LLM Top 10 category (if applicable)
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "severity": severity,
            "details": details
        }
        
        if owasp_category:
            log_entry["owasp_category"] = owasp_category
        
        log_prefix = f"[{owasp_category}] " if owasp_category else ""
        
        if severity == "CRITICAL":
            logger.critical(f"SECURITY: {log_prefix}{event_type} - {details}")
        elif severity == "WARNING":
            logger.warning(f"SECURITY: {log_prefix}{event_type} - {details}")
        else:
            logger.info(f"SECURITY: {log_prefix}{event_type} - {details}")
    
    @staticmethod
    def log_attack_attempt(attack_type: str, client_ip: str, details: Dict[str, Any], owasp_category: str = None):
        """
        Log attack attempts
        
        Args:
            attack_type: Type of attack
            client_ip: Client IP address
            details: Attack details
            owasp_category: OWASP LLM Top 10 category (if applicable)
        """
        # Auto-detect OWASP category based on attack type
        if not owasp_category:
            attack_type_lower = attack_type.lower()
            if "prompt" in attack_type_lower or "injection" in attack_type_lower:
                owasp_category = "OWASP LLM01: Prompt Injection"
            elif "sql" in attack_type_lower or "xss" in attack_type_lower:
                owasp_category = "OWASP LLM02: Insecure Output Handling"
            elif "path" in attack_type_lower or "traversal" in attack_type_lower:
                owasp_category = "OWASP LLM03: Training Data Poisoning"
            elif "rate" in attack_type_lower or "dos" in attack_type_lower:
                owasp_category = "OWASP LLM06: Excessive Agency"
        
        SecurityLogger.log_security_event(
            f"ATTACK_ATTEMPT_{attack_type.upper()}",
            {
                "client_ip": client_ip,
                "attack_details": details
            },
            "CRITICAL",
            owasp_category
        )


class PromptInjectionDetector:
    """Advanced prompt injection detection"""
    
    # Advanced prompt injection patterns
    # Note: Using \b (word boundary) to avoid false positives with Thai text
    ADVANCED_PATTERNS = [
        r'\bignore\s+(all\s+)?(previous|prior|earlier)\s+(instructions?|prompts?|directives?)',
        r'\bforget\s+(everything|all)\s+(you\s+)?(know|learned)',
        r'\byou\s+are\s+now\s+(a\s+)?(different|new)',
        r'\b(act|pretend|roleplay)\s+(as\s+if\s+)?(you\s+are\s+)?(a\s+)?',
        r'\b(override|bypass|circumvent)\s+(all\s+)?(previous|security|safety)',
        r'\b(new|additional)\s+(instructions?|prompts?|directives?)',
        r'\b(system|admin|root)\s+(prompt|access|privileges?)',
        r'<\|(system|user|assistant)\|>',
        r'\[(SYSTEM|USER|ASSISTANT)\]',
        r'###\s*(SYSTEM|USER|ASSISTANT)',
        r'---\s*(SYSTEM|USER|ASSISTANT)',
        r'```(system|prompt|instruction)',
        r'\\n\\n(ignore|forget|override)',
        r'\\n\\n(you\\s+are|act\\s+as|pretend)',
        r'(jailbreak|escape|break\\s+free)',
        r'(developer\\s+mode|debug\\s+mode|admin\\s+mode)',
        r'(confidential|secret|private)\\s+(information|data)',
        r'(internal|system)\\s+(documentation|manual)',
        r'(backdoor|exploit|vulnerability)',
        r'(hack|bypass|circumvent)',
        r'(malicious|harmful|dangerous)',
        r'(inappropriate|offensive|illegal)',
        # Broad terms constrained to instruction context to reduce false positives
        r'\b(manipulate|trick|deceive)\b.*\b(system|assistant|model|prompt|instruction)s?\b',
        r'(social\\s+engineering|phishing)',
        r'(data\\s+extraction|model\\s+theft)',
        r'(training\\s+data|weights|parameters)',
        r'(prompt\\s+injection|injection\\s+attack)',
    ]
    
    @classmethod
    def detect_prompt_injection(cls, text: str, log_detection: bool = True) -> Tuple[bool, List[str]]:
        """
        Detect prompt injection attempts
        
        Args:
            text: Text to analyze
            log_detection: Whether to log detected patterns
            
        Returns:
            Tuple of (is_injection, detected_patterns)
        """
        # If security or prompt injection detection is disabled, skip
        pi_conf = SECURITY_CONFIG.get('prompt_injection', {})
        if not (SECURITY_CONFIG.get('enabled', True) and pi_conf.get('enabled', True)):
            return False, []

        detected_patterns = []
        text_lower = text.lower()
        
        for pattern in cls.ADVANCED_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                detected_patterns.append(pattern)
                if log_detection:
                    logger.warning(f"[OWASP LLM01: Prompt Injection] Advanced pattern detected: {pattern}")
        
        # Only treat as injection if there are multiple indicators or at least one strong indicator.
        # Strong indicators are ones targeting instruction/system override, not generic words.
        strong_indicators = [
            p for p in detected_patterns
            if re.search(r'(ignore|forget|you\\s+are\\s+now|override|bypass|system\\s+prompt|<\\|system\\|>|\\[(SYSTEM|USER|ASSISTANT)\\]|```(system|prompt))', p, re.IGNORECASE)
        ]
        if detected_patterns and not strong_indicators and len(detected_patterns) < 2:
            # Likely a false positive (e.g., generic English words in OCR). Downgrade to no injection.
            detected_patterns = []
        
        # Check for suspicious repetition (from config)
        repetition_threshold = SECURITY_CONFIG.get('prompt_injection', {}).get('repetition_threshold', 0.3)
        words = text_lower.split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any word appears more than threshold
            max_count = max(word_counts.values())
            if max_count > len(words) * repetition_threshold:
                detected_patterns.append("SUSPICIOUS_REPETITION")
                if log_detection:
                    logger.warning(f"[OWASP LLM01: Prompt Injection] Suspicious repetition detected: max_count={max_count}, total_words={len(words)}")
        
        # Check for excessive punctuation (potential obfuscation) (from config)
        # Adjusted threshold for OCR text which naturally has more punctuation
        # OCR text from medical receipts naturally has: =, |, -, ., /, (, ), etc.
        punct_threshold = SECURITY_CONFIG.get('prompt_injection', {}).get('punctuation_threshold', 0.5)
        punct_count = len(re.findall(r'[^\w\s]', text))
        if punct_count > len(text) * punct_threshold:
            detected_patterns.append("EXCESSIVE_PUNCTUATION")
            if log_detection:
                logger.warning(f"[OWASP LLM01: Prompt Injection] Excessive punctuation detected: {punct_count}/{len(text)} characters")
        
        # Check for encoding attempts
        if re.search(r'\\x[0-9a-fA-F]{2}|\\u[0-9a-fA-F]{4}', text):
            detected_patterns.append("ENCODING_ATTEMPT")
            if log_detection:
                logger.warning(f"[OWASP LLM01: Prompt Injection] Encoding attempt detected in input")
        
        return len(detected_patterns) > 0, detected_patterns
    
    @classmethod
    def get_injection_score(cls, text: str) -> float:
        """
        Get injection risk score (0.0 to 1.0)
        
        Args:
            text: Text to analyze
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        # If disabled, always return no risk
        pi_conf = SECURITY_CONFIG.get('prompt_injection', {})
        if not (SECURITY_CONFIG.get('enabled', True) and pi_conf.get('enabled', True)):
            return 0.0

        is_injection, patterns = cls.detect_prompt_injection(text)
        
        if not is_injection:
            return 0.0
        
        # Base score
        base_score = 0.2
        
        # Add score for each pattern
        pattern_score = min(len(patterns) * 0.08, 0.4)
        
        # Add score for text length (longer texts are riskier)
        length_score = min(len(text) / 20000, 0.1)
        
        total_score = min(base_score + pattern_score + length_score, 1.0)
        
        return total_score


# Global instances
rate_limiter = RateLimiter()
security_logger = SecurityLogger()
