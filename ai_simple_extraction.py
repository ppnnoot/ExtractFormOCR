"""
AI Simple Extraction - Simplified Flow
1. Receive OCR text + form_id
2. Send to AI API to extract data by JSON keys
3. Map extracted keys to template_json structure
"""

import json
form_id = None
import os
import time
import logging
import re
import copy
from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
import uuid

# Import our modules
from multi_ocr_adapter import MultiOCRManager, OCRResult
from template_api_manager import TemplateAPIManager
from log_manager import get_log_manager
from ocr_correction import correct_ocr_text, validate_ocr_corrections

logger = logging.getLogger(__name__)


class TwoStepAIPipeline:
    """
    Two-Step AI Pipeline wrapper for backward compatibility
    Combines SimpleAIExtractor, JSONFormatter, and TemplateAPIManager
    """
    
    def __init__(self, config_path: str):
        """Initialize pipeline with config file"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Initialize components
        self.template_manager = TemplateAPIManager(self.config)
        self.simple_extractor = SimpleAIExtractor(self.config)
        self.json_formatter = JSONFormatter()
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }
    
    def process_document(self, image_path: str, template: str = "medical_receipt") -> Dict[str, Any]:
        """
        Process document from image file
        For backward compatibility - delegates to OCR + extraction
        """
        try:
            # This is a simplified version - full implementation would use OCR adapter
            # For now, return error message suggesting to use /extract/text endpoint
            logger.warning("process_document() called but full OCR processing not implemented in simplified version")
            logger.info("Please use /extract/image endpoint instead")
            
            return {
                'success': False,
                'error': 'process_document() not fully implemented. Use /extract/image endpoint instead.'
            }
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            self.stats['failed'] += 1
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        return {
            'total_processed': self.stats['total_processed'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0
        }


class SimpleAIExtractor:
    """Simplified AI Extractor - Extract JSON keys from AI, then map to template"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_config = config.get('ai_extraction', {})
        self.api_config = self.ai_config.get('api', {})
        
        # API settings
        self.endpoint = self.api_config.get('endpoint')
        self.model = self.api_config.get('model')
        self.temperature = self.api_config.get('temperature', 0.1)
        self.top_p = self.api_config.get('top_p', 0.8)
        self.max_tokens = self.api_config.get('max_tokens', 4000)
        self.frequency_penalty = self.api_config.get('frequency_penalty', 0)
        self.presence_penalty = self.api_config.get('presence_penalty', 0)
        self.seed = self.api_config.get('seed', None)
        self.stop = self.api_config.get('stop', None)
        self.timeout = self.api_config.get('timeout', 120)
        self.max_retries = self.api_config.get('max_retries', 3)
        self.auth_token = self.api_config.get('auth_token')
        self.response_format = self.ai_config.get('response_format', 'json')
        self.simple_list_max_tokens = self.ai_config.get('simple_list_max_tokens', 4000)

        # Prompt optimization settings
        self.prompt_optimization = self.ai_config.get('prompt_optimization', {})
        self.max_ocr_results = self.prompt_optimization.get('max_ocr_results', 200)
        self.deduplicate_billing_items = self.prompt_optimization.get('deduplicate_billing_items', True)

        # Template manager for fetching Template_json keys
        self.template_manager = TemplateAPIManager(config)
        self.template_form_id_mapping = config.get('templates', {}).get('form_id_mapping', {})

        # Set logging level for this module
        log_config = config.get('logging', {})
        if 'level' in log_config:
            log_level = getattr(logging, log_config.get('level', 'INFO').upper())
            logging.getLogger(__name__).setLevel(log_level)
            logger.setLevel(log_level)

    def extract_simple(self, ocr_results: List[Dict[str, Any]], 
                      save_request: bool = True, template: str = "medical_receipt") -> Dict[str, Any]:
        """
        Simplified extraction flow:
        1. Load template_json to get expected keys
        2. Send OCR text to AI API with template keys guidance
        3. Parse JSON response from AI
        4. Return extracted data with keys matching template
        
        Args:
            ocr_results: OCR results
            save_request: Save AI request/response to file for debugging
            template: Template to use for extraction (form_id like 'HL0000050')
        """
        import requests
        
        # Step 1: Load template_json to get expected keys
        form_id = self._resolve_form_id(template)
        template_config = self.template_manager.get_template(form_id) if form_id else None
        template_structure = self._extract_template_structure(template_config)
        template_keys = self._extract_template_keys(template_structure)
        
        # Step 2: Prepare OCR text
        ocr_text = self._prepare_ocr_text(ocr_results)
        ocr_line_count = len([line for line in ocr_text.split('\n') if line.strip()])
        logger.info(f"📊 OCR text stats: {ocr_line_count} non-empty lines, {len(ocr_text)} characters")
        
        if self.response_format == 'simple_list':
            prompt = self._create_list_prompt(ocr_text, template_keys)
            template_keys_guidance = self._build_template_keys_guidance(template_keys) + "\nReturn ONLY [K]/[L1]/[L2]/[L3] lines. No JSON. No explanations."
        else:
            prompt = self._create_simple_prompt(ocr_text, template_keys)
            template_keys_guidance = self._build_template_keys_guidance(template_keys)
        
        # Step 4: Call AI API
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': ('You are an EXPERT at extracting billing lines from Thai medical receipts. ' +
                                               ('Return ONLY simple list with [L1]/[L2]/[L3] markers.' if self.response_format == 'simple_list' else 'Return ONLY valid JSON, no explanations or markdown.'))},
                {'role': 'system', 'content': template_keys_guidance},
                {'role': 'user', 'content': prompt}
            ],
            'seed': self.seed,
            'stop': self.stop,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'max_tokens': (self.simple_list_max_tokens if self.response_format == 'simple_list' else self.max_tokens),
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty
        }
        
        # Save request if enabled
        request_id = None
        if save_request:
            request_id = self._save_ai_request(payload, prompt)
        
        # Step 5: Retry logic
        best_result = None
        best_item_count = 0
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"🔍 Calling AI API (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Save response if enabled
                    if save_request and request_id:
                        self._save_ai_response(request_id, result, content)
                    
                    logger.info(f"📝 AI Response (first 500 chars): {content[:500]}")
                    
                    if self.response_format == 'simple_list':
                        parsed = self._parse_simple_response(content, ocr_text, template_keys)
                    else:
                        parsed = self._parse_ai_json_response(content, template_keys)
                    
                    item_count = len(parsed.get('billing_items', []))
                    order_item_count = len(parsed.get('_order_items_data', []))
                    total_extracted = item_count + order_item_count
                    extraction_ratio = (total_extracted / ocr_line_count * 100) if ocr_line_count > 0 else 0
                    
                    logger.info(f"✅ Parsed {item_count} billing items + {order_item_count} order items = {total_extracted} total items")
                    logger.info(f"📊 Extraction ratio: {extraction_ratio:.1f}% ({total_extracted}/{ocr_line_count} lines)")
                    
                    # Validate extraction completeness
                    if ocr_line_count > 50 and total_extracted < ocr_line_count * 0.3:
                        logger.warning(f"⚠️ Low extraction rate: {extraction_ratio:.1f}% - May need to increase max_tokens")
                    elif ocr_line_count > 100 and total_extracted < ocr_line_count * 0.4:
                        logger.warning(f"⚠️ Possible incomplete extraction for large document ({ocr_line_count} lines)")
                    
                    # Log parsed data for debugging
                    if item_count == 0:
                        # Check if AI response has billing_items but we didn't parse them
                        try:
                            json_obj_check = json.loads(content) if isinstance(content, str) else content
                            if 'billing_items' in json_obj_check:
                                raw_billing = json_obj_check.get('billing_items', [])
                                logger.warning(f"⚠️ No billing items parsed! Raw billing_items count: {len(raw_billing) if isinstance(raw_billing, list) else 0}")
                                if isinstance(raw_billing, list) and len(raw_billing) > 0:
                                    logger.warning(f"⚠️ First item keys: {list(raw_billing[0].keys()) if isinstance(raw_billing[0], dict) else 'N/A'}")
                        except:
                            pass
                    
                    # Keep best result (prefer higher total_extracted count)
                    if best_result is None or total_extracted > best_item_count:
                        best_result = parsed
                        best_item_count = total_extracted
                    
                    # Determine if extraction is complete enough
                    is_complete = False
                    if ocr_line_count <= 30:
                        # Small document: expect at least 30% extraction
                        is_complete = total_extracted >= ocr_line_count * 0.3
                    elif ocr_line_count <= 100:
                        # Medium document: expect at least 40% extraction
                        is_complete = total_extracted >= ocr_line_count * 0.4
                    else:
                        # Large document: expect at least 35% extraction (more lenient due to headers/footers)
                        is_complete = total_extracted >= ocr_line_count * 0.35
                    
                    # Return immediately if extraction is complete
                    if is_complete and best_result is not None:
                        other_fields_count = len([k for k, v in best_result.items() if v is not None and k not in ['billing_items', '_order_items_data']])
                        logger.info(f"✅ Extraction completed (attempt {attempt + 1}): {total_extracted} total items ({extraction_ratio:.1f}%), {other_fields_count} other fields")
                        return best_result
                    elif best_result is not None:
                        logger.warning(f"⚠️ Extraction incomplete (attempt {attempt + 1}): {total_extracted} items ({extraction_ratio:.1f}%) - Will retry...")
                        # Continue to retry
                    else:
                        logger.warning(f"⚠️ No result parsed (attempt {attempt + 1}) - Will retry...")
                else:
                    logger.warning(f"❌ AI API returned status {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ AI API timeout (attempt {attempt + 1})")
            except Exception as e:
                logger.warning(f"❌ AI API error (attempt {attempt + 1}): {e}")
            
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        # Return best result or empty structure
        if best_result is not None:
            best_billing = len(best_result.get('billing_items', []) or [])
            best_order = len(best_result.get('_order_items_data', []) or [])
            best_total = best_billing + best_order
            best_ratio = (best_total / ocr_line_count * 100) if ocr_line_count > 0 else 0
            
            logger.warning(f"⚠️ Returning best result after {self.max_retries} attempts:")
            logger.warning(f"   - {best_total} total items ({best_ratio:.1f}% of {ocr_line_count} OCR lines)")
            logger.warning(f"   - {best_billing} billing items + {best_order} order items")
            
            if best_ratio < 30:
                logger.error(f"❌ CRITICAL: Extraction rate is very low ({best_ratio:.1f}%)")
                logger.error(f"   Possible causes:")
                logger.error(f"   1. max_tokens too low (current: {self.simple_list_max_tokens if self.response_format == 'simple_list' else self.max_tokens})")
                logger.error(f"   2. AI model timeout or truncation")
                logger.error(f"   3. Complex document structure")
            
            return best_result
        
        logger.error("❌ AI extraction yielded no parseable result after all retries; returning empty structure")
        return self._create_empty_result(template_keys)

    def _resolve_form_id(self, template: str) -> Optional[str]:
        """Resolve form_id from template parameter"""
        if isinstance(template, str) and re.match(r'^HL\d{7}$', template):
            return template
        return self.template_form_id_mapping.get(template) or self.template_form_id_mapping.get(
            self.config.get('templates', {}).get('default', 'medical_receipt')
        )

    def _extract_template_structure(self, template_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract template_structure from template_config"""
        if not template_config:
            return None
        
        if 'Template_json' in template_config:
            template_json = template_config['Template_json']
            if isinstance(template_json, str):
                try:
                    return json.loads(template_json)
                except json.JSONDecodeError:
                    logger.error("Failed to parse Template_json")
                    return None
            return template_json
        elif 'template_structure' in template_config:
            return template_config['template_structure']
        
        return None

    def _extract_template_keys(self, template_structure: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Extract expected keys from template_structure"""
        keys = {
            'top_level': [],
            'billing_fields': ['billing_code', 'billing_desc', 'amount', 'discount', 'net_amount']
        }
        
        if not template_structure:
            # Default keys
            keys['top_level'] = ['hospital_name', 'hn', 'an', 'gross_amount', 'admission_date']
            return keys
        
        # Extract from documents[0].document_info
        try:
            documents = template_structure.get('documents', [])
            if documents and isinstance(documents, list) and len(documents) > 0:
                doc_info = documents[0].get('document_info', [])
                if isinstance(doc_info, list):
                    for field in doc_info:
                        code = field.get('code')
                        if code and code != 'billing_items' and code != 'order_items':
                            keys['top_level'].append(code)
                        elif code == 'billing_items':
                            # Extract billing item structure
                            billing_template = field.get('value', [])
                            if billing_template and isinstance(billing_template, list) and len(billing_template) > 0:
                                billing_fields = billing_template[0].get('value', [])
                                if isinstance(billing_fields, list):
                                    keys['billing_fields'] = [f.get('code') for f in billing_fields if f.get('code')]
        except Exception as e:
            logger.warning(f"Failed to extract template keys: {e}")
        
        # Fallback to defaults if empty
        if not keys['top_level']:
            keys['top_level'] = ['hospital_name', 'hn', 'an', 'gross_amount', 'admission_date']
        
        return keys

    def _prepare_ocr_text(self, ocr_results: List[Dict[str, Any]]) -> str:
        """Prepare OCR text from OCR results"""
        texts = []
        for result in ocr_results[:self.max_ocr_results]:
            text = result.get('text', '').strip()
            if text:
                texts.append(text)
        return '\n'.join(texts)

    def _create_simple_prompt(self, ocr_text: str, template_keys: Dict[str, List[str]]) -> str:
        """Create enhanced prompt for AI extraction with detailed business rules"""
        top_keys = ', '.join(template_keys.get('top_level', []))
        billing_keys = ' | '.join(template_keys.get('billing_fields', []))
        
        prompt = f"""Extract data from the following OCR text and return as JSON:

OCR Text:
{ocr_text}

Required JSON structure:
{{
  "{'", "'.join(template_keys.get('top_level', []))}",
  "billing_items": [
    {{
      "billing_code": "string (e.g., '1.2.1', '1.6.1(1)')",
      "billing_desc": "string (description)",
      "item_level": "integer (1, 2, or 3)",
      "amount": "decimal",
      "discount": "decimal",
      "net_amount": "decimal",
      "grouporder_items": "array (optional, for L2 items)"
    }}
  ],
  "order_items": [
    {{
      "billing_code": "string (original code from document)",
      "billing_desc": "string (medicine name)",
      "amount": "decimal",
      "discount": "decimal",
      "net_amount": "decimal"
    }}
  ]
}}

CRITICAL BUSINESS RULES:

1. BILLING_CODE VALIDATION:
   - billing_code MUST contain digits (e.g., "1.2.1", "1.6.1(1)", "2.1")
   - If billing_code is missing or contains only text (like "ค่าบริการ", "รวม", "ยอดรวม"), set it to null
   - DO NOT use descriptions as billing_code (e.g., "ค่าบริการโรงพยาบาล" is NOT a valid code)

2. ITEM LEVELS (Hierarchical Structure - 3 Levels):
   
   Level 1 (L1) - billing_items: Main categories (หมวดหมู่)
   - Examples: "1.1.1" (คายาและสารอาหารทางเสนเลือด), "1.1.2" (ค่าเวชภัณฑ์), "1.2.1" (ค่าตรวจรักษา)
   - These are top-level categories in billing_items array
   - Each L1 code should appear ONLY ONCE in billing_items (no duplicates)
   - May contain grouporder_items (L2 items) if there are sub-categories
   - Set item_level: 1
   - If an L1 item has multiple L2 sub-items, group them all under the same L1 item
   
   Level 2 (L2) - grouporder_items: Sub-categories (รายการ)
   - Examples: "1.1.1(18)" (ค่าน้ำเกลือ), "1.1.1(2)" (ยากลับบ้าน), "1.1.2(1)" (เวชภัณฑ์ 1), "1.1.7(1)" (อุปกรณ์)
   - These are sub-items within grouporder_items array of L1 items
   - Each L2 item belongs to ONE L1 parent
   - Set item_level: 2
   - L2 items do NOT contain order_items - L3 items go directly to root-level order_items array
   
   Level 3 (L3) - order_items: Individual items (รายการย่อย)
   - Examples: "D-5-S/2 (no set) SOFT BAGS (1000 mL)", "H.S.S (100 ml) Injection", "AIR-X Tablet (120 mg)", "Buscopan Tablet (10 mg)"
   - These are the actual medicine/drug items or detailed line items
   - MUST be placed in order_items array at ROOT LEVEL (NOT nested in grouporder_items)
   - billing_code should match the L2 parent code (e.g., if parent is "1.1.1(18)", use "1.1.1(18)" in order_items)
   - Set item_level: 3 (optional, but recommended for clarity)
   
   CRITICAL RULES:
   - DO NOT create duplicate L1 items (e.g., two "1.1.1" entries)
   - L3 items (order_items) should NOT be nested inside grouporder_items
   - L3 items should reference their L2 parent's billing_code
   - If an L1 has multiple L2 items, group all L2 items under the same L1 item

3. BILLING_ITEMS vs ORDER_ITEMS (CRITICAL):
   
   ORDER_ITEMS (Medicine/Drug Items Only):
   - Include items with codes starting with: "1.1.1", "1.1.12", "1.1.14"
   - Include items with medicine keywords in description: "ยา", "ยาผู้ป่วย", "ยากลับบ้าน", "medicine", "drug", "medication"
   - Include items with dosage forms: "tablet", "capsule", "injection", "syrup", "mg", "ml", "mcg", "g"
   - Include items with patterns like: "Tab", "Cap", "Inj", "ORS", "(100 ml)", "(10 mg)"
   - DO NOT include: "ค่าบริการพยาบาล", "ค่าบริการโรงพยาบาล", "ตรวจรักษา", "lab", "x-ray", "imaging", "fee"
   
   BILLING_ITEMS (All Other Items):
   - Include all items that are NOT medicine/drug items
   - Include service fees, lab tests, room charges, etc.
   - Structure: L1 (billing_items) → L2 (grouporder_items) → L3 items go to order_items if they are medicine
   - Example structure:
     * L1: "1.1.1" (คายาและสารอาหารทางเสนเลือด) in billing_items
     * L2: "1.1.1(18)" (ค่าน้ำเกลือ) in grouporder_items of L1
     * L3: "D-5-S/2 (no set) SOFT BAGS (1000 mL)" should go to order_items (if medicine) OR stay in grouporder_items (if not medicine)

4. AGGREGATE LINES (EXCLUDE):
   - DO NOT include lines with keywords: "รวม", "ยอดรวม", "สุทธิ", "total", "summary"
   - These are calculated totals, not individual items

5. FIELD REQUIREMENTS:
   - billing_code: Must be a code with digits, or null if not found
   - billing_desc: Full description from document
   - item_level: 1, 2, or 3 (based on hierarchy)
   - amount: Decimal number (use "0.00" if not found)
   - discount: Decimal number (use "0.00" if not found)
   - net_amount: Decimal number (calculate as amount - discount if not explicitly shown)

6. EXTRACTION INSTRUCTIONS:
   - Extract ALL items from the document
   - Use exact field names: {top_keys}
   - For billing_items, include: {billing_keys}
   - For order_items, extract ONLY medicine/drug items as defined above
   - Keep order_items separate from billing_items (at root level, NOT nested in grouporder_items)
   - Preserve hierarchical structure:
     * L1 items → billing_items array (each L1 code appears ONLY ONCE)
     * L2 items → grouporder_items array within their parent L1 item
     * L3 medicine items → order_items array (root level, separate from billing_items)
     * L3 non-medicine items → can stay in grouporder_items or be L2 items
   - IMPORTANT: Group all L2 items under their parent L1 item (do NOT create duplicate L1 items)
   - IMPORTANT: L3 items in order_items should use billing_code from their L2 parent (or L1 if no L2)
   - Return ONLY valid JSON, no explanations or markdown
   - If a field is not found, use null (not empty string)
   
7. STRUCTURE EXAMPLE (Complete 3-Level Hierarchy):
   {{
     "billing_items": [
       {{
         "billing_code": "1.1.1",
         "billing_desc": "คายาและสารอาหารทางเสนเลือด",
         "item_level": 1,
         "amount": "6716.00",
         "discount": "671.60",
         "net_amount": "6044.40",
         "grouporder_items": [
           {{
             "billing_code": "1.1.1(18)",
             "billing_desc": "ค่าน้ำเกลือ",
             "item_level": 2,
             "amount": "2146.00",
             "discount": "214.60",
             "net_amount": "1931.40"
           }},
           {{
             "billing_code": "1.1.1(2)",
             "billing_desc": "ยากลับบ้าน (Home Medication)",
             "item_level": 2,
             "amount": "849.00",
             "discount": "84.90",
             "net_amount": "764.10"
           }}
         ]
       }},
       {{
         "billing_code": "1.1.2",
         "billing_desc": "ค่าเวชภัณฑ์",
         "item_level": 1,
         "amount": "1906.00",
         "discount": "0.00",
         "net_amount": "1906.00",
         "grouporder_items": [
           {{
             "billing_code": "1.1.2(1)",
             "billing_desc": "เวชภัณฑ์ 1 วัสดุสิ้นเปลืองทางการแพทย์",
             "item_level": 2,
             "amount": "1906.00",
             "discount": "0.00",
             "net_amount": "1906.00"
           }}
         ]
       }}
     ],
     "order_items": [
       {{
         "billing_code": "1.1.1(18)",
         "billing_desc": "D-5-S/2 (no set) SOFT BAGS (1000 mL)",
         "amount": "1410.00",
         "discount": "141.00",
         "net_amount": "1269.00"
       }},
       {{
         "billing_code": "1.1.1(18)",
         "billing_desc": "H.S.S (100 ml) Injection",
         "amount": "736.00",
         "discount": "73.60",
         "net_amount": "662.40"
       }},
       {{
         "billing_code": "1.1.1",
         "billing_desc": "AIR-X Tablet * (120 mg) * - สีทอง-",
         "amount": "84.00",
         "discount": "8.40",
         "net_amount": "75.60"
       }},
       {{
         "billing_code": "1.1.1(2)",
         "billing_desc": "AIR-X Tablet * (120 mg) * - สีทอง- 5 Tablet",
         "amount": "50.00",
         "discount": "5.00",
         "net_amount": "45.00"
       }}
     ]
   }}
   
   NOTE: 
   - L1 "1.1.1" appears ONLY ONCE with multiple L2 items in grouporder_items
   - L3 items in order_items use the billing_code from their L2 parent (e.g., "1.1.1(18)" for items under "ค่าน้ำเกลือ")
   - L3 items that belong directly to L1 (without L2) use the L1 code (e.g., "1.1.1" for items directly under "คายา")

8. OUTPUT FORMAT:
   - Return clean JSON with proper structure
   - **⚠️ CRITICAL: Extract EVERY single line item from the document. Do NOT skip any items.**
   - **⚠️ If document has 2 pages, extract items from BOTH pages completely.**
   - **⚠️ Count total lines in OCR text and ensure you extract matching number of items.**
   - **⚠️ If OCR text has 50+ lines, your response should have 40+ billing items.**
   - Verify: Total billing_items + order_items should be close to number of OCR lines
   - All decimal values as strings (e.g., "15.00", "2200.00")
   - All codes as strings (e.g., "1.2.1", "1.6.1(1)")
   - No extra fields beyond what's specified
   - **⚠️ IMPORTANT: Extract until you reach the end of OCR text, not just first page.**
"""
        return prompt

    def _create_list_prompt(self, ocr_text: str, template_keys: Dict[str, List[str]]) -> str:
        top_keys = ', '.join(template_keys.get('top_level', []))
        billing_fields = template_keys.get('billing_fields', [])
        include_totals = 'total_amout' in billing_fields
        rules = [
            ("- Keep decimals as strings (e.g., 1410.00)"),
            ("- Use actual billing codes with digits for [L1]/[L2] (e.g., 1.1.1, 1.1.1(2))"),
            ("- Medicine/drug details go as [L3] under their [L2] parent context"),
            ("- If a header value is not found, use '-'"),
        ]
        if include_totals:
            rules.insert(0, "- Include summary lines such as 'รวม' when they carry amounts")
        else:
            rules.insert(0, "- Exclude totals: รวม, ยอดรวม, สุทธิ, total, summary (billing section)")

        return (
            "Extract billing lines and header fields from the OCR text and return ONLY a compact simple list.\n\n"
            "Header format: \n"
            "[K] key | value\n\n"
            "Billing format: \n"
            "[L1] code | desc | amount | discount | net\n"
            "[L2] code | desc | amount | discount | net\n"
            "[L3] item_desc | quantity | amount | discount | net\n\n"
            f"Header Keys: {top_keys}\n\n"
            "Rules:\n" + "\n".join(rules) + "\n\n" +
            "OCR Text:\n" + ocr_text
        )

    def _build_template_keys_guidance(self, template_keys: Dict[str, List[str]]) -> str:
        """Build enhanced guidance string for AI with business rules"""
        top_keys = ', '.join(template_keys.get('top_level', []))
        billing_keys = ' | '.join(template_keys.get('billing_fields', []))
        
        return (
            f"CRITICAL EXTRACTION RULES:\n"
            f"1. Top-level fields: {top_keys}\n"
            f"2. Billing item fields: {billing_keys} | item_level\n"
            f"3. Order item fields: billing_code | billing_desc | amount | discount | net_amount (ONLY medicine/drug items)\n"
            f"4. billing_code MUST contain digits (e.g., '1.2.1', '1.6.1(1)') - use null if missing or invalid\n"
            f"5. Order items: codes starting with '1.1.1', '1.1.12', '1.1.14' OR medicine keywords (ยา, tablet, injection, mg, ml)\n"
            f"6. Billing items: all other items (services, fees, tests)\n"
            f"7. EXCLUDE aggregate lines: 'รวม', 'ยอดรวม', 'สุทธิ', 'total', 'summary'\n"
            f"8. Set item_level: 1 (L1), 2 (L2), or 3 (L3) based on hierarchy\n"
            f"9. All decimal values as strings (e.g., '15.00', '2200.00')"
        )

    def _parse_ai_json_response(self, content: str, template_keys: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Simplified JSON parser - only parse JSON, no line-based parsing
        Extract keys directly from AI JSON response
        """
        # Try to extract JSON from response
        json_obj = None
        
        # First, try direct JSON parse
        try:
            json_obj = json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON substring
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1 and end > start:
                try:
                    json_obj = json.loads(content[start:end+1])
                except json.JSONDecodeError:
                    logger.error("Failed to parse JSON from AI response")
                    return self._create_empty_result(template_keys)
            else:
                logger.error("No JSON found in AI response")
                return self._create_empty_result(template_keys)
        
        # Extract data using template keys
        extracted = {}
        
        # Extract top-level fields
        for key in template_keys.get('top_level', []):
            # Try direct match first
            if key in json_obj:
                extracted[key] = json_obj[key]
            else:
                # Try common variations
                variations = self._get_key_variations(key)
                for var in variations:
                    if var in json_obj:
                        extracted[key] = json_obj[var]
                        break
        
        # Extract billing_items - keep ALL items from AI response as simple list
        billing_items = []
        raw_items = json_obj.get('billing_items', [])
        if isinstance(raw_items, dict):
            raw_items = [raw_items]
        
        if isinstance(raw_items, list):
            logger.info(f"📋 Processing {len(raw_items)} billing items from AI response")
            for idx, item in enumerate(raw_items):
                if isinstance(item, dict):
                    # Keep all fields from AI response, normalize keys
                    billing_item = dict(item)  # Copy all fields
                    
                    # Log first item structure for debugging
                    if idx == 0:
                        logger.info(f"📋 First billing item fields: {list(billing_item.keys())}")
                    
                    # Validate and normalize billing_code/item_no
                    # Check if billing_code is a real code or just a description
                    billing_code = billing_item.get('billing_code') or billing_item.get('code') or billing_item.get('item_no')
                    
                    if billing_code:
                        billing_code_str = str(billing_code).strip()

                        # Simple validation: if no digits or contains description keywords, set to "-"
                        has_digits = bool(re.search(r'\d', billing_code_str))
                        has_description_keywords = any(keyword in billing_code_str for keyword in [
                            'ค่าบริการ', 'ค่าใช้จ่าย', 'โรงพยาบาล', 'รวม', 'ทั้งหมด', 'พยาบาล', 'กรมธรรม์', 'เก็บจาก'
                        ])

                        if not has_digits or has_description_keywords:
                            logger.warning(f"⚠️ billing_code '{billing_code_str}' is not a valid code (no digits: {not has_digits}, has keywords: {has_description_keywords}), setting to '-'")
                            billing_item['billing_code'] = "-"
                            billing_item['code'] = "-"
                            if 'item_no' in billing_item:
                                billing_item['item_no'] = "-"
                        else:
                            # Valid code - normalize
                            if 'item_no' in billing_item:
                                if 'billing_code' not in billing_item:
                                    billing_item['billing_code'] = billing_item['item_no']
                                if 'code' not in billing_item:
                                    billing_item['code'] = billing_item['item_no']
                    else:
                        # No billing_code found - set to "-"
                        billing_item['billing_code'] = "-"
                        billing_item['code'] = "-"
                        logger.warning(f"⚠️ No billing_code found for item {idx}, setting to '-'")
                    
                    # Normalize billing_desc to desc if needed
                    if 'billing_desc' in billing_item and 'desc' not in billing_item:
                        billing_item['desc'] = billing_item['billing_desc']
                    
                    # Always add item (even if billing_code is "-")
                    billing_items.append(billing_item)
            
            logger.info(f"✅ Extracted {len(billing_items)} billing items (preserving all fields)")
        
        # Filter out aggregate/summary rows (strict match)
        def _is_aggregate_row(it: Dict[str, Any]) -> bool:
            code_text = str(it.get('billing_code') or it.get('code') or it.get('item_no') or '').strip().lower()
            desc_text = str(it.get('billing_desc') or it.get('desc') or '').strip().lower()
            aggregate_keywords = ['รวม', 'ยอดรวม', 'total', 'summary', 'สุทธิ']
            def is_exact_agg(t: str) -> bool:
                return t in aggregate_keywords or re.fullmatch(r'(รวม|ยอดรวม|total|summary|สุทธิ)\s*[:：\-]?\s*', t) is not None
            return is_exact_agg(code_text) or is_exact_agg(desc_text)
        
        if billing_items:
            before = len(billing_items)
            billing_items = [it for it in billing_items if not _is_aggregate_row(it)]
            after = len(billing_items)
            if after != before:
                logger.info(f"🧹 Removed {before - after} aggregate/summary rows from billing items")
        
        # Separate order_items (medicine and service items) from billing_items
        order_items = []
        filtered_billing_items = []

        # Define patterns for order items (based on business rules)
        order_item_patterns = [
            r'^1\.1\.1',  # Medicine items (ค่ายา) - includes 1.1.1, 1.1.1(2), etc.
            r'^1\.1\.12', # Nursing services (ค่าบริการพยาบาล)
            r'^1\.1\.14', # Hospital services (ค่าบริการโรงพยาบาล)
        ]

        # Medicine keywords for additional detection
        medicine_keywords = [
            # TH generic
            'ยา', 'ยาผู้ป่วย', 'ยาผู้ป่วยใน', 'ยาผู้ป่วยนอก', 'ยากลับบ้าน',
            # EN generic
            'medicine', 'drug', 'medication', 'home medication',
            # Forms/Units (TH)
            'เม็ด', 'แคปซูล', 'ฉีด', 'ขวด', 'ซอง',
            # Exclude non-medicine services will be handled separately
        ]
        # Regex patterns strongly indicating medicine items by dosage/forms (case-insensitive)
        medicine_desc_patterns = [
            re.compile(r'\b(tab|tablet|cap|capsule|inj|injection|syrup|oral|susp)\b', re.I),
            re.compile(r'\b\d+\s?(mg|ml|mcg|g)\b', re.I),
            re.compile(r'\(\s*\d+\s?(mg|ml|mcg|g)\s*\)', re.I),
            re.compile(r'\bors\b', re.I),  # Oral Rehydration Salt
        ]
        # Service keywords to explicitly keep out of order_items
        non_medicine_service_keywords = [
            'ค่าบริการพยาบาล', 'ค่าบริการโรงพยาบาล', 'ตรวจรักษา', 'lab', 'laboratory',
            'x-ray', 'imaging', 'fee', 'ค่าตรวจ', 'ค่าห้อง', 'ค่าอาหาร', 'อาหารผู้ป่วย'
        ]

        for item in billing_items:
            item_code = str(item.get('billing_code') or item.get('code') or item.get('item_no', '')).strip()
            item_desc = str(item.get('billing_desc') or item.get('desc', '')).lower()

            # Check if it's an order item based on code pattern or description
            is_order_item = False

            # Check code patterns
            for pattern in order_item_patterns:
                if re.match(pattern, item_code):
                    is_order_item = True
                    break

            # Check description keywords if not already identified as order item
            if not is_order_item:
                # Skip clear non-medicine services
                if any(svc in item_desc for svc in non_medicine_service_keywords):
                    is_order_item = False
                # Medicine keywords
                elif any(keyword in item_desc for keyword in medicine_keywords):
                    is_order_item = True
                # Dosage/form regex patterns
                elif any(p.search(item_desc) for p in medicine_desc_patterns):
                    is_order_item = True

            # Categorize the item
            if is_order_item:
                order_items.append(item)
                logger.info(f"📋 Categorized as order item: {item_code} - {item_desc[:50]}...")
            else:
                filtered_billing_items.append(item)
                logger.debug(f"📋 Kept as billing item: {item_code} - {item_desc[:50]}...")

        # Assign synthetic codes for missing or invalid codes to keep mapping stable
        bi_seq = 1
        for it in filtered_billing_items:
            code_val = str(it.get('billing_code') or it.get('code') or it.get('item_no') or '').strip()
            if code_val == '-' or code_val == '':
                synth = f"BI{bi_seq:03d}"
                it['billing_code'] = synth
                it['code'] = synth
                bi_seq += 1
        oi_seq = 1
        for it in order_items:
            code_val = str(it.get('billing_code') or it.get('code') or it.get('item_no') or '').strip()
            if code_val == '-' or code_val == '':
                synth = f"OI{oi_seq:03d}"
                it['billing_code'] = synth
                it['code'] = synth
                oi_seq += 1
        
        extracted['billing_items'] = filtered_billing_items
        extracted['_order_items_data'] = order_items

        logger.info(f"✅ Categorized items: {len(filtered_billing_items)} billing items, {len(order_items)} order items (medicine/services)")
        
        # Deduplicate if enabled
        if self.deduplicate_billing_items:
            extracted['billing_items'] = self._deduplicate_items(extracted['billing_items'])
        
        # Keep as simple list - hierarchical structure will be built in JSONFormatter based on template
        logger.info(f"✅ Extracted {len(extracted.get('billing_items', []))} billing items (simple list)")
        
        return extracted

    def _parse_simple_response(self, content: str, ocr_text: str = "", template_keys: Dict[str, List[str]] = None) -> Dict[str, Any]:
        try:
            from tools.map_from_ai_json import parse_hierarchical, build_flat_arrays
        except Exception:
            parse_hierarchical = None
            build_flat_arrays = None

        extracted: Dict[str, Any] = {}
        if template_keys:
            header = {}
            lines = [ln.strip() for ln in (content or '').splitlines() if ln.strip()]
            for ln in lines:
                if ln.startswith('[K]'):
                    body = ln[3:].strip()
                    parts = [p.strip() for p in body.split('|')]
                    if len(parts) >= 2:
                        k = parts[0]
                        v = '|'.join(parts[1:]).strip()
                        header[k] = v
            for key in template_keys.get('top_level', []):
                if key in header:
                    extracted[key] = header.get(key)
        if parse_hierarchical and build_flat_arrays:
            billing_items_hier, l3_count = parse_hierarchical(content or "")
            billing_flat, order_flat = build_flat_arrays(billing_items_hier)
            # Prefer hierarchical for accurate Template_json mapping
            extracted['billing_items'] = billing_items_hier
            extracted['_order_items_data'] = order_flat
        else:
            extracted['billing_items'] = []
            extracted['_order_items_data'] = []

        missing = [k for k in (template_keys.get('top_level', []) if template_keys else []) if extracted.get(k) in [None, '-', '']]
        if missing:
            top = self._extract_top_level_from_ocr(ocr_text or "")
            for key in missing:
                if extracted.get(key) in [None, '-', '']:
                    val = top.get(key)
                    if val is not None:
                        extracted[key] = val

        return extracted

    def _extract_top_level_from_ocr(self, text: str) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        try:
            m = re.search(r'HN\s*:\s*([A-Za-z0-9\-]+)', text)
            if m:
                data['hn'] = m.group(1)
            m = re.search(r'AN\s*:\s*([A-Za-z0-9\-]+)', text)
            if m:
                data['an'] = m.group(1)
            m = re.search(r'EN\s*:\s*([A-Za-z0-9\-]+)', text)
            if m:
                data['vn_en'] = m.group(1)
            else:
                m = re.search(r'VN\s*:\s*([A-Za-z0-9\-]+)', text)
                if m:
                    data['vn_en'] = m.group(1)
            m = re.search(r'Admission\s*Date\s*:\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})', text)
            if m:
                data['admission_date'] = m.group(1)
            if 'admission_date' not in data:
                m = re.search(r'วันที่เข้ารับการรักษา\s*:\s*([0-9]{2}\/[0-9]{2}\/[0-9]{4})', text)
                if m:
                    data['admission_date'] = m.group(1)
            m = re.search(r'Patient\s*Name\s*:\s*(.+?)\s*HN\s*:', text, re.S)
            if m:
                name = m.group(1).strip()
                data['patient_name'] = name
            else:
                m = re.search(r'(?:ชื่อผู้ป่วย|ชื่อคนไข้)\s*:\s*(.+?)(?:\s+(?:HN|AN|EN|VN)\s*:|$)', text, re.S)
                if m:
                    data['patient_name'] = m.group(1).strip()
            m = re.search(r'โรงพยาบาล\s*:?\s*([^\d\n,]+?)\s+\d', text)
            if m:
                data['hospital_name'] = m.group(1).strip()
            else:
                m = re.search(r'โรงพยาบาล\s*:?\s*([^\n]+)\s+[^\n]*?HN', text)
                if m:
                    hospital = m.group(1).strip()
                    hospital = re.sub(r'\s*เลขที่.*$', '', hospital)
                    hospital = re.sub(r'\s{2,}', ' ', hospital)
                    data['hospital_name'] = hospital
                else:
                    m = re.search(r'โรงพยาบาล\s*:?\s*([^\n]+?)(?:\s+(?:HN|AN|EN|ที่อยู่|Address|โทรศัพท์|วันที่เข้ารับ|วันที่ออก)|$)', text)
                    if m:
                        data['hospital_name'] = m.group(1).strip()
                    else:
                        m = re.search(r'(โรงพยาบาล[^\n]*?)(?:\s+Print\s+Date|\s+Patient\s+Name|\s+ใบแจ้ง|\n|$)', text)
                        if m:
                            hospital = m.group(1).strip()
                            hospital = re.sub(r'\s{2,}', ' ', hospital)
                            data['hospital_name'] = hospital
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            num_pat = r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?'
            for ln in lines[::-1]:
                if 'สุทธิ' in ln:
                    nums = re.findall(num_pat, ln)
                    if nums:
                        s = nums[-1].replace(',', '').replace(' ', '')
                        try:
                            data['net_amount_total'] = f"{float(s):.2f}"
                        except:
                            pass
                    break
            for ln in lines[::-1]:
                if ('ส่วนลด' in ln or 'Discount' in ln) and not re.search(r'รายการ', ln):
                    nums = re.findall(num_pat, ln)
                    if nums:
                        s = nums[-1].replace(',', '').replace(' ', '')
                        try:
                            data['discount_total'] = f"{float(s):.2f}"
                        except:
                            pass
                    break
            for ln in lines[::-1]:
                if ('รวม' in ln or 'ยอดรวม' in ln) and 'สุทธิ' not in ln:
                    nums = re.findall(num_pat, ln)
                    if nums:
                        s = nums[-1].replace(',', '').replace(' ', '')
                        try:
                            data['amount_total'] = f"{float(s):.2f}"
                        except:
                            pass
                    break
        except Exception:
            pass
        return data

    def _get_key_variations(self, key: str) -> List[str]:
        """Get common variations of a key name"""
        variations = {
            'hospital_name': ['hospital_name', 'HOSPITAL_NAME', 'hospital', 'hospital_th', 'ชื่อโรงพยาบาล'],
            'hn': ['hn', 'HN', 'patient_id', 'เลขhn'],
            'an': ['an', 'AN', 'en', 'EN', 'vn', 'VN'],
            'gross_amount': ['gross_amount', 'total_amount', 'grand_total', 'total', 'ยอดรวม'],
            'admission_date': ['admission_date', 'date_of_issue', 'visit_date', 'วันที่รับเข้า'],
            'billing_code': ['billing_code', 'code', 'item_no', 'no'],
            'billing_desc': ['billing_desc', 'desc', 'description', 'item_desc'],
            'amount': ['amount', 'price', 'unit_price', 'total_amount'],
            'discount': ['discount', 'disc'],
            'net_amount': ['net_amount', 'net', 'net_total', 'total']
        }
        return variations.get(key, [key])

    def _create_empty_result(self, template_keys: Dict[str, List[str]]) -> Dict[str, Any]:
        """Create empty result structure"""
        result = {}
        for key in template_keys.get('top_level', []):
            result[key] = None
        result['billing_items'] = []
        return result

    def _deduplicate_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate billing items"""
        seen = set()
        unique = []
        for item in items:
            code = item.get('billing_code') or item.get('code') or item.get('item_no', '')
            desc = item.get('billing_desc') or item.get('desc', '')
            key = (code, desc)
            if key not in seen:
                seen.add(key)
                unique.append(item)
        return unique

    def _build_hierarchical_structure(self, flat_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build hierarchical billing items structure (L1, L2, L3)
        
        Structure:
        - L1: Top-level items (e.g., "1.1", "1.2", "2.1")
        - L2: Sub-items under L1 (e.g., "1.1.1", "1.1.2")
        - L3: Detail items under L2 (e.g., "1.1.1(1)", "1.1.1(2)")
        
        Returns hierarchical structure with grouporder_items and order_items
        """
        if not flat_items:
            return []
        
        # Normalize item codes and detect levels
        normalized_items = []
        for item in flat_items:
            # Get code from various possible keys
            code = item.get('billing_code') or item.get('code') or item.get('item_no', '')
            # Normalize: if item_no exists, also set as billing_code and code
            if 'item_no' in item and not code:
                code = item['item_no']
            
            desc = item.get('billing_desc') or item.get('desc', '')
            amount = item.get('amount', 0)
            discount = item.get('discount', 0)
            net_amount = item.get('net_amount', 0)
            
            # Detect level from code pattern
            level, parent_code = self._detect_item_level(code)
            
            normalized_items.append({
                'code': code,
                'desc': desc,
                'amount': amount,
                'discount': discount,
                'net_amount': net_amount,
                'item_level': level,
                'parent_code': parent_code,
                'original': item
            })
        
        # Group items by level
        l1_items = {}  # {code: item}
        l2_items = {}  # {code: item}
        l3_items = []  # List of items
        
        for item in normalized_items:
            level = item['item_level']
            code = item['code']
            
            if level == 1:
                l1_items[code] = item
            elif level == 2:
                l2_items[code] = item
            elif level == 3:
                l3_items.append(item)
        
        # Build hierarchical structure
        hierarchical = []
        
        # Process L1 items
        for l1_code, l1_item in sorted(l1_items.items()):
            l1_structure = {
                'billing_code': l1_code,
                'billing_desc': l1_item['desc'],
                'amount': l1_item['amount'],
                'discount': l1_item['discount'],
                'net_amount': l1_item['net_amount'],
                'item_level': 1,
                'grouporder_items': []
            }
            
            # Find L2 items under this L1
            l2_children = {}
            for l2_code, l2_item in l2_items.items():
                if l2_item['parent_code'] == l1_code:
                    l2_children[l2_code] = l2_item
            
            # Process L2 items
            for l2_code, l2_item in sorted(l2_children.items()):
                l2_structure = {
                    'billing_code': l2_code,
                    'billing_desc': l2_item['desc'],
                    'amount': l2_item['amount'],
                    'discount': l2_item['discount'],
                    'net_amount': l2_item['net_amount'],
                    'item_level': 2,
                    'order_items': []
                }
                
                # Find L3 items under this L2
                l3_children = []
                for l3_item in l3_items:
                    if l3_item['parent_code'] == l2_code:
                        l3_children.append({
                            'billing_code': l3_item['code'],
                            'billing_desc': l3_item['desc'],
                            'amount': l3_item['amount'],
                            'discount': l3_item['discount'],
                            'net_amount': l3_item['net_amount'],
                            'item_level': 3
                        })
                
                l2_structure['order_items'] = sorted(l3_children, key=lambda x: x['billing_code'])
                l1_structure['grouporder_items'].append(l2_structure)
            
            # If no L2 children, check for direct L3 children
            if not l1_structure['grouporder_items']:
                direct_l3 = []
                for l3_item in l3_items:
                    if l3_item['parent_code'] == l1_code:
                        direct_l3.append({
                            'billing_code': l3_item['code'],
                            'billing_desc': l3_item['desc'],
                            'amount': l3_item['amount'],
                            'discount': l3_item['discount'],
                            'net_amount': l3_item['net_amount'],
                            'item_level': 3
                        })
                
                if direct_l3:
                    # Create dummy L2 to hold L3 items
                    l1_structure['grouporder_items'].append({
                        'billing_code': f"{l1_code}1",
                        'billing_desc': l1_item['desc'],
                        'amount': 0,
                        'discount': 0,
                        'net_amount': 0,
                        'item_level': 2,
                        'order_items': sorted(direct_l3, key=lambda x: x['billing_code'])
                    })
            
            hierarchical.append(l1_structure)
        
        # If no L1 items found, return flat structure as L1
        if not hierarchical:
            for item in normalized_items:
                hierarchical.append({
                    'billing_code': item['code'],
                    'billing_desc': item['desc'],
                    'amount': item['amount'],
                    'discount': item['discount'],
                    'net_amount': item['net_amount'],
                    'item_level': 1,
                    'grouporder_items': []
                })
        
        logger.info(f"✅ Built hierarchical structure: {len(hierarchical)} L1 items")
        return hierarchical

    def _detect_item_level(self, code: str) -> Tuple[int, Optional[str]]:
        """
        Detect item level from billing code
        
        Returns: (level, parent_code)
        - L1: "1.1", "1.2", "2.1" -> level=1, parent=None
        - L2: "1.1.1", "1.1.2" -> level=2, parent="1.1"
        - L3: "1.1.1(1)", "1.1.1(2)" -> level=3, parent="1.1.1"
        """
        if not code:
            return 1, None
        
        code = str(code).strip()
        
        # Check for L3 pattern: has parentheses like "1.1.1(1)"
        if '(' in code and ')' in code:
            # Extract base code before parentheses
            base_code = code.split('(')[0].strip()
            # Parent is the base code
            return 3, base_code
        
        # Count dots to determine level
        parts = code.split('.')
        
        if len(parts) == 2:
            # L1: "1.1", "2.1"
            return 1, None
        elif len(parts) == 3:
            # L2: "1.1.1", "1.1.2"
            parent = '.'.join(parts[:2])  # "1.1"
            return 2, parent
        elif len(parts) >= 4:
            # L3 or deeper: "1.1.1.1"
            parent = '.'.join(parts[:-1])  # Remove last part
            return 3, parent
        
        # Default to L1
        return 1, None

    def _save_ai_request(self, payload: Dict[str, Any], prompt: str) -> str:
        """Save AI request to file for debugging"""
        request_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + str(uuid.uuid4())[:8]
        
        debug_dir = './output/ai_debug/requests'
        os.makedirs(debug_dir, exist_ok=True)
        
        request_file = os.path.join(debug_dir, f"request_{request_id}.json")
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump({
                'request_id': request_id,
                'timestamp': datetime.now().isoformat(),
                'endpoint': self.endpoint,
                'model': self.model,
                'payload': payload,
                'prompt': prompt
            }, f, ensure_ascii=False, indent=2)
        
        logger.info(f"AI request saved: {request_file}")
        return request_id

    def _save_ai_response(self, request_id: str, result: Dict[str, Any], content: str):
        """Save AI response to file for debugging"""
        debug_dir = './output/ai_debug/responses'
        os.makedirs(debug_dir, exist_ok=True)
        
        # Save as JSON
        response_file_json = os.path.join(debug_dir, f"response_{request_id}.json")
        with open(response_file_json, 'w', encoding='utf-8') as f:
            json.dump({
                'request_id': request_id,
                'timestamp': datetime.now().isoformat(),
                'result': result,
                'content': content
            }, f, ensure_ascii=False, indent=2)
        
        # Save as text
        response_file_txt = os.path.join(debug_dir, f"response_{request_id}.txt")
        with open(response_file_txt, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"AI response saved: {response_file_json}")


# Keep JSONFormatter class unchanged for backward compatibility
class JSONFormatter:
    """Format simple extracted data into complex nested JSON structure"""
    
    @staticmethod
    def format_to_medical_receipt_json(simple_data: Dict[str, Any], 
                                       metadata: Dict[str, Any] = None,
                                       transaction_no: str = None,
                                       document_code: str = None,
                                       template_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convert simple data to full Medical Receipt JSON format using Template_json structure from API"""
        
        # Generate transaction_no if not provided
        if not transaction_no:
            import time
            transaction_no = f"TX{int(time.time() * 1000)}"
        
        # Get document_code from template API (formId) or generate if not provided
        if not document_code:
            if template_config and 'form_id' in template_config:
                document_code = template_config['form_id']
                logger.info(f"Using document_code from template API: {document_code}")
            else:
                document_code = f"CM{int(time.time() * 1000)}"
                logger.warning(f"Template API not available, using generated document_code: {document_code}")
        
        # Get document_type from template API (docName) or use default
        if template_config and 'document_type' in template_config:
            document_type = template_config['document_type']
            logger.info(f"Using document_type from template API: {document_type}")
        else:
            document_type = "Detail"
            logger.warning(f"Template API not available, using default document_type: {document_type}")
        
        # Use Template_json/template_structure from API if available
        template_structure = None
        # Ensure local form_id variable exists for downstream mapping
        try:
            form_id = template_config.get('form_id') if template_config else None
        except Exception:
            form_id = None
        if template_config:
            if 'Template_json' in template_config:
                logger.info("Using Template_json structure from API")
                template_json = template_config['Template_json']
                if isinstance(template_json, str):
                    try:
                        template_json = json.loads(template_json)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse Template_json: {e}")
                        template_json = None
                if template_json:
                    import copy
                    template_structure = copy.deepcopy(template_json)
            elif 'template_structure' in template_config:
                logger.info("Using template_structure parsed from API")
                import copy
                template_structure = copy.deepcopy(template_config['template_structure'])
        
        # Log template structure for debugging
        if template_structure:
            logger.info(f"📋 Template structure loaded: {json.dumps(template_structure, indent=2, ensure_ascii=False)[:500]}...")
            if 'documents' in template_structure and len(template_structure['documents']) > 0:
                doc_info = template_structure['documents'][0].get('document_info', [])
                logger.info(f"📋 Template has {len(doc_info)} document_info fields")
                for field in doc_info:
                    if field.get('code') == 'billing_items':
                        billing_template = field.get('value', [])
                        logger.info(f"📋 Billing items template structure: {len(billing_template)} template items")
                        if billing_template and len(billing_template) > 0:
                            logger.info(f"📋 First billing item template: {json.dumps(billing_template[0], indent=2, ensure_ascii=False)[:300]}...")

        if template_structure:
            # Fill in the template with extracted data
            if 'documents' in template_structure and len(template_structure['documents']) > 0:
                document = template_structure['documents'][0]
                
                # Set document metadata
                document['document_code'] = document_code
                document['document_type'] = document_type
                if template_config and template_config.get('form_id') == 'HL0000053':
                    document['page'] = "1-2"
                    document['total_page'] = "2"
                else:
                    document['page'] = "1"
                    document['total_page'] = "1"
                
                # Prepare simple data
                simple = dict(simple_data or {})
                
                # Map extracted data to template fields
                if 'document_info' in document:
                    for field in document['document_info']:
                        field_code = field.get('code')
                        field_type = field.get('type', 'string')
                        
                        if field_code == 'billing_items' and field_type == 'array':
                            # Handle billing items
                            template_billing_structure = field.get('value', [])
                            # Attach form_id into simple_data for downstream mapping rules
                            try:
                                _fid = None
                                if isinstance(metadata, dict):
                                    _fid = metadata.get('form_id')
                                if not _fid and template_config:
                                    _fid = template_config.get('form_id')
                                simple_data['_form_id'] = _fid
                            except Exception:
                                simple_data['_form_id'] = None
                            billing_items = JSONFormatter._build_billing_items_from_template(
                                simple_data, template_billing_structure
                            )
                            field['value'] = billing_items
                            field['accuracyRate'] = None
                            field['page'] = "1"
                        elif field_code == 'order_items' and field_type == 'array':
                            # Handle order items (medicine items - รายการยา)
                            order_items_data = simple.get('_order_items_data', [])
                            template_order_items = field.get('value', [])
                            
                            if order_items_data:
                                # Normalize order items to match template field names
                                normalized_order_items = []
                                for oi in order_items_data:
                                    code_val = oi.get('billing_code') or oi.get('code') or oi.get('item_no') or "-"
                                    desc_val = oi.get('billing_desc') or oi.get('desc') or "-"
                                    amount_val = oi.get('amount') if oi.get('amount') is not None else 0
                                    discount_val = oi.get('discount') if oi.get('discount') is not None else 0
                                    net_val = oi.get('net_amount') if oi.get('net_amount') is not None else (amount_val - discount_val if isinstance(amount_val, (int, float)) and isinstance(discount_val, (int, float)) else 0)
                                    
                                    enriched = dict(oi)  # keep originals too
                                    # Populate template-expected fields
                                    enriched.setdefault('item_id', code_val)
                                    enriched.setdefault('item_desc', desc_val)
                                    enriched.setdefault('item_amont', amount_val)  # template uses 'item_amont'
                                    enriched.setdefault('amount', amount_val)
                                    enriched.setdefault('discount', discount_val)
                                    enriched.setdefault('net_amount', net_val)
                                    enriched.setdefault('billing_item_no', code_val)  # best effort link
                                    normalized_order_items.append(enriched)
                                
                                # Map order items to template structure - ONLY map fields defined in template
                                if template_order_items and len(template_order_items) > 0:
                                    template_order_item = template_order_items[0]
                                    mapped_order_items = []
                                    for order_item in normalized_order_items:
                                        import copy
                                        order_template = copy.deepcopy(template_order_item)
                                        # Use strict mapping for order_items - only map template-defined fields
                                        order_template = JSONFormatter._map_item_to_template_strict(order_item, order_template)
                                        mapped_order_items.append(order_template)
                                    field['value'] = mapped_order_items
                                    logger.info(f"✅ Mapped {len(mapped_order_items)} order items (medicine items) to template structure")
                                else:
                                    # No template structure, use as-is
                                    field['value'] = normalized_order_items
                                    logger.info(f"✅ Using {len(order_items_data)} order items as-is (no template structure)")
                            elif template_order_items:
                                field['value'] = template_order_items
                            else:
                                field['value'] = []
                            field['accuracyRate'] = None
                            field['page'] = "1"
                        else:
                            # Map simple fields
                            value = simple.get(field_code)
                            if value is not None:
                                field['value'] = JSONFormatter._normalize_value(value, field_type)
                                field['accuracyRate'] = None
                            else:
                                field['value'] = "-"
                                field['accuracyRate'] = None
                            field['page'] = "1"
            
            # Set transaction_no at root level
            template_structure['transaction_no'] = transaction_no
            
            return JSONFormatter._normalize_all_values(template_structure)
        else:
            logger.error("Template structure unavailable")
            raise RuntimeError("Template_json not available; cannot format output.")
    
    @staticmethod
    def _build_billing_items_from_template(simple_data: Dict[str, Any],
                                          template_billing_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build billing items array using template structure from API
        Supports both flat and hierarchical structures (L1, L2, L3)
        """
        extracted_billing = simple_data.get('billing_items', [])
        
        if not extracted_billing:
            logger.warning("No billing items extracted, returning template structure with default values")
            return template_billing_items if template_billing_items else []
        
        if not template_billing_items:
            logger.warning("No template billing structure found, returning extracted items as-is")
            return extracted_billing
        
        # Since we already separated order_items, extracted_billing contains only billing items
        # Map directly to template structure (keeping original order)
        logger.info(f"Building billing items: extracted_count={len(extracted_billing)}, template_count={len(template_billing_items)}")
        # If items include nested grouporder_items, build hierarchical mapping
        if any(isinstance(it, dict) and it.get('grouporder_items') for it in extracted_billing):
            result = JSONFormatter._build_hierarchical_billing_from_template(
                extracted_billing, template_billing_items
            )
        else:
            result = JSONFormatter._map_hierarchical_to_template(
                extracted_billing, template_billing_items
            )

        form_id = simple_data.get('_form_id')
        if form_id == 'HL0000054':
            try:
                has_summary = False
                total_sum = 0.0
                for mapped in result:
                    vals = {f.get('code'): f.get('value') for f in (mapped.get('value') or []) if isinstance(f, dict)}
                    desc = vals.get('billing_desc')
                    if isinstance(desc, str) and ('รวม' in desc or (desc or '').lower() == 'summary'):
                        has_summary = True
                    amt = vals.get('total_amout')
                    if isinstance(amt, str):
                        try:
                            total_sum += float(amt.replace(',', ''))
                        except:
                            pass
                    elif isinstance(amt, (int, float)):
                        total_sum += float(amt)
                if not has_summary and total_sum > 0 and template_billing_items:
                    import copy
                    summary_item = copy.deepcopy(template_billing_items[0])
                    for f in summary_item.get('value', []):
                        code = f.get('code')
                        if code == 'billing_code':
                            f['value'] = ''
                        elif code == 'billing_desc':
                            f['value'] = 'รวม'
                        elif code == 'total_amout':
                            f['value'] = f"{total_sum:.2f}"
                        elif code == 'discount':
                            f['value'] = '0.00'
                        elif code == 'policy_covered':
                            f['value'] = f"{total_sum:.2f}"
                        elif code == 'policy_not_covered':
                            f['value'] = '0.00'
                    result.append(summary_item)
            except Exception:
                pass

        if form_id == 'HL0000052':
            try:
                seen = set()
                filtered = []
                for mapped in result:
                    vals = {f.get('code'): f.get('value') for f in (mapped.get('value') or []) if isinstance(f, dict)}
                    code = vals.get('billing_code') or ''
                    base = code.split('(')[0].strip()
                    key = base or code
                    if key and key not in seen:
                        seen.add(key)
                        filtered.append(mapped)
                result = filtered
            except Exception:
                pass

        return result
    
    @staticmethod
    def _build_hierarchical_billing_from_template(extracted_billing: List[Dict[str, Any]],
                                                  template_billing_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Build hierarchical billing items matching template structure"""
        if not template_billing_items or len(template_billing_items) == 0:
            return extracted_billing
        
        template_item = template_billing_items[0]
        result = []
        
        # Process each L1 item
        for l1_item in extracted_billing:
            if l1_item.get('item_level') != 1:
                continue
            
            # Clone template structure for L1
            import copy
            l1_template = copy.deepcopy(template_item)
            
            # Map L1 fields
            l1_template = JSONFormatter._map_item_to_template(l1_item, l1_template)
            
            # Process grouporder_items (L2)
            grouporder_items = l1_item.get('grouporder_items', [])
            if grouporder_items:
                l1_template['grouporder_items'] = []
                for l2_item in grouporder_items:
                    l2_template = copy.deepcopy(template_item)
                    l2_template = JSONFormatter._map_item_to_template(l2_item, l2_template)
                    
                    # Process order_items (L3)
                    order_items = l2_item.get('order_items', [])
                    if order_items:
                        l2_template['order_items'] = []
                        for l3_item in order_items:
                            l3_template = copy.deepcopy(template_item)
                            l3_template = JSONFormatter._map_item_to_template(l3_item, l3_template)
                            l2_template['order_items'].append(l3_template)
                    
                    l1_template['grouporder_items'].append(l2_template)
            
            result.append(l1_template)
        
        logger.info(f"✅ Built {len(result)} hierarchical billing items from template")
        return result
    
    @staticmethod
    def _build_hierarchical_structure_from_flat(flat_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Build hierarchical structure according to business rules:
        - If L1 has L3 children (sub-items with parentheses) → use L3 items as billing items
        - If L1 has no L3 children → use L1 item itself as billing item
        
        Example:
        - 1.1.1 has children 1.1.1(1), 1.1.1(2) → use 1.1.1(1), 1.1.1(2) as billing items
        - 2.1 has no children → use 2.1 itself as billing item
        """
        if not flat_items:
            return []
        
        # Normalize and detect levels
        normalized_items = []
        for item in flat_items:
            code = item.get('billing_code') or item.get('code') or item.get('item_no', '')
            desc = item.get('billing_desc') or item.get('desc', '')
            amount = item.get('amount', 0)
            discount = item.get('discount', 0)
            net_amount = item.get('net_amount', 0)
            
            # Detect level
            level, parent_code = JSONFormatter._detect_item_level(code)
            
            normalized_items.append({
                'code': code,
                'desc': desc,
                'amount': amount,
                'discount': discount,
                'net_amount': net_amount,
                'item_level': level,
                'parent_code': parent_code,
                'original': item
            })
        
        # Group by level
        l1_items = {}
        l2_items = {}
        l3_items = []
        
        for item in normalized_items:
            level = item['item_level']
            code = item['code']
            if level == 1:
                l1_items[code] = item
            elif level == 2:
                l2_items[code] = item
            elif level == 3:
                l3_items.append(item)
        
        # Build billing items according to business rules
        billing_items_result = []
        
        for l1_code, l1_item in sorted(l1_items.items()):
            # Find all L3 children under this L1 (directly or through L2)
            l3_children = []
            
            # Check direct L3 children
            for l3_item in l3_items:
                if l3_item['parent_code'] == l1_code:
                    l3_children.append(l3_item)
            
            # Check L3 children through L2
            for l2_code, l2_item in l2_items.items():
                if l2_item['parent_code'] == l1_code:
                    for l3_item in l3_items:
                        if l3_item['parent_code'] == l2_code:
                            l3_children.append(l3_item)
            
            # Business rule: If has L3 children, use L3 items; otherwise use L1 itself
            if l3_children:
                # Use L3 items as billing items
                logger.info(f"L1 {l1_code} has {len(l3_children)} L3 children → using L3 items as billing items")
                for l3_item in sorted(l3_children, key=lambda x: x['code']):
                    billing_items_result.append({
                        'billing_code': l3_item['code'],
                        'billing_desc': l3_item['desc'],
                        'amount': l3_item['amount'],
                        'discount': l3_item['discount'],
                        'net_amount': l3_item['net_amount'],
                        'item_level': 3,
                        'parent_code': l3_item['parent_code'],
                        'original': l3_item['original']
                    })
            else:
                # Use L1 item itself as billing item
                logger.info(f"L1 {l1_code} has no L3 children → using L1 item itself as billing item")
                billing_items_result.append({
                    'billing_code': l1_code,
                    'billing_desc': l1_item['desc'],
                    'amount': l1_item['amount'],
                    'discount': l1_item['discount'],
                    'net_amount': l1_item['net_amount'],
                    'item_level': 1,
                    'parent_code': None,
                    'original': l1_item['original']
                })
        
        # Handle L2 items that are not under any L1 (standalone)
        for l2_code, l2_item in sorted(l2_items.items()):
            # Check if this L2 is already processed under an L1
            already_processed = False
            for l1_code in l1_items.keys():
                if l2_item['parent_code'] == l1_code:
                    already_processed = True
                    break
            
            if not already_processed:
                # Check if L2 has L3 children
                l3_children = []
                for l3_item in l3_items:
                    if l3_item['parent_code'] == l2_code:
                        l3_children.append(l3_item)
                
                if l3_children:
                    # Use L3 items
                    for l3_item in sorted(l3_children, key=lambda x: x['code']):
                        billing_items_result.append({
                            'billing_code': l3_item['code'],
                            'billing_desc': l3_item['desc'],
                            'amount': l3_item['amount'],
                            'discount': l3_item['discount'],
                            'net_amount': l3_item['net_amount'],
                            'item_level': 3,
                            'parent_code': l3_item['parent_code'],
                            'original': l3_item['original']
                        })
                else:
                    # Use L2 item itself
                    billing_items_result.append({
                        'billing_code': l2_code,
                        'billing_desc': l2_item['desc'],
                        'amount': l2_item['amount'],
                        'discount': l2_item['discount'],
                        'net_amount': l2_item['net_amount'],
                        'item_level': 2,
                        'parent_code': l2_item['parent_code'],
                        'original': l2_item['original']
                    })
        
        # Handle standalone L3 items (not under any L1 or L2)
        for l3_item in l3_items:
            # Check if already processed
            already_processed = False
            for result_item in billing_items_result:
                if result_item['billing_code'] == l3_item['code']:
                    already_processed = True
                    break
            
            if not already_processed:
                # Use L3 item itself
                billing_items_result.append({
                    'billing_code': l3_item['code'],
                    'billing_desc': l3_item['desc'],
                    'amount': l3_item['amount'],
                    'discount': l3_item['discount'],
                    'net_amount': l3_item['net_amount'],
                    'item_level': 3,
                    'parent_code': l3_item['parent_code'],
                    'original': l3_item['original']
                })
        
        logger.info(f"✅ Built billing items structure: {len(billing_items_result)} items (using business rules)")
        return billing_items_result
    
    @staticmethod
    def _detect_item_level(code: str) -> Tuple[int, Optional[str]]:
        """Detect item level from billing code"""
        if not code:
            return 1, None
        
        code = str(code).strip()
        
        # Check for L3 pattern: has parentheses
        if '(' in code and ')' in code:
            base_code = code.split('(')[0].strip()
            return 3, base_code
        
        # Count dots
        parts = code.split('.')
        if len(parts) == 2:
            return 1, None
        elif len(parts) == 3:
            parent = '.'.join(parts[:2])
            return 2, parent
        elif len(parts) >= 4:
            parent = '.'.join(parts[:-1])
            return 3, parent
        
        return 1, None
    
    @staticmethod
    def _map_hierarchical_to_template(hierarchical_billing: List[Dict[str, Any]],
                                      template_billing_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Map billing items structure to template structure
        Note: hierarchical_billing is now a flat list of billing items (not hierarchical)
        following business rules: use L3 if exists, otherwise use L1/L2
        """
        if not template_billing_items or len(template_billing_items) == 0:
            return hierarchical_billing
        
        template_item = template_billing_items[0]
        result = []
        
        # Map each billing item to template structure - use strict mode to match template exactly
        for billing_item in hierarchical_billing:
            import copy
            item_template = copy.deepcopy(template_item)
            # Use strict recursive mapping to preserve template structure exactly (no extra fields)
            item_template = JSONFormatter._map_item_to_template_strict_recursive(billing_item, item_template)
            result.append(item_template)
        
        # If template is summary-style (uses total_amout), ensure a 'รวม' line exists
        try:
            template_item_fields = template_item.get('value', []) if isinstance(template_item, dict) else []
            uses_total = any((isinstance(f, dict) and f.get('code') == 'total_amout') for f in template_item_fields)
            if uses_total:
                has_summary = False
                total_sum = 0.0
                for mapped in result:
                    vals = {f.get('code'): f.get('value') for f in mapped.get('value', []) if isinstance(f, dict)}
                    desc = vals.get('billing_desc')
                    if isinstance(desc, str) and ('รวม' in desc or 'summary' in desc.lower()):
                        has_summary = True
                    amt = vals.get('total_amout')
                    try:
                        if isinstance(amt, str):
                            total_sum += float(amt.replace(',', ''))
                        elif isinstance(amt, (int, float)):
                            total_sum += float(amt)
                    except:
                        pass
                if not has_summary and total_sum > 0:
                    import copy
                    summary_item = copy.deepcopy(template_item)
                    # Fill fields
                    filled = []
                    for f in summary_item.get('value', []):
                        code = f.get('code')
                        if code == 'billing_code':
                            f['value'] = ''
                        elif code == 'billing_desc':
                            f['value'] = 'รวม'
                        elif code == 'total_amout':
                            f['value'] = f"{total_sum:.2f}"
                        elif code == 'discount':
                            f['value'] = '0.00'
                        elif code == 'policy_covered':
                            f['value'] = f"{total_sum:.2f}"
                        elif code == 'policy_not_covered':
                            f['value'] = '0.00'
                        filled.append(f)
                    summary_item['value'] = filled
                    result.append(summary_item)
        except Exception as _e:
            pass
        logger.info(f"✅ Mapped {len(result)} billing items to template structure")
        return result
    
    @staticmethod
    def _map_item_to_template(item: Dict[str, Any], template_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted item data to template item structure
        DEPRECATED: Use _map_item_to_template_strict_recursive for strict template compliance
        This function is kept for backward compatibility but should not add extra fields
        """
        # Use strict recursive mapping to ensure template compliance
        return JSONFormatter._map_item_to_template_strict_recursive(item, template_item)
    
    @staticmethod
    def _map_item_to_template_strict_recursive(item: Dict[str, Any], template_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted item data to template item structure (STRICT RECURSIVE MODE)
        Only maps fields that exist in template - does NOT add extra fields from AI response
        Handles nested structures (billing_item → grouporder_items → order_items) recursively
        Used for billing_items to ensure clean structure matching template exactly
        """
        if 'value' in template_item and isinstance(template_item['value'], list):
            template_field_codes = {f.get('code') for f in template_item['value']}
            
            # Map fields that exist in template
            for field in template_item['value']:
                template_field_code = field.get('code')
                field_type = field.get('type', 'string')
                
                # Handle nested arrays (grouporder_items, order_items)
                if field_type == 'array' and 'value' in field and isinstance(field['value'], list):
                    # Check if this is a nested structure
                    nested_template = field['value'][0] if len(field['value']) > 0 else None
                    
                    if nested_template and 'code' in nested_template:
                        nested_code = nested_template.get('code')
                        # Get nested data from item
                        nested_data = item.get(template_field_code) or item.get(nested_code)
                        
                        if nested_data and isinstance(nested_data, list):
                            # Recursively map nested items
                            mapped_nested = []
                            for nested_item in nested_data:
                                if isinstance(nested_item, dict):
                                    nested_template_copy = copy.deepcopy(nested_template)
                                    mapped_nested_item = JSONFormatter._map_item_to_template_strict_recursive(nested_item, nested_template_copy)
                                    mapped_nested.append(mapped_nested_item)
                            
                            if mapped_nested:
                                field['value'] = mapped_nested
                                field['accuracyRate'] = None
                            else:
                                field['value'] = []
                                field['accuracyRate'] = None
                        else:
                            field['value'] = []
                            field['accuracyRate'] = None
                        
                        field['page'] = "1"
                        continue
                
                # Try to get value from item using various key names
                extracted_value = None
                source_key = None
                
                # Direct match
                if template_field_code in item:
                    extracted_value = item[template_field_code]
                    source_key = template_field_code
                # Common variations
                elif template_field_code == 'item_no':
                    # Try item_no, billing_code, code
                    extracted_value = item.get('item_no') or item.get('billing_code') or item.get('code')
                    
                    # Validate if it's a real code (not a long description)
                    if extracted_value:
                        extracted_value_str = str(extracted_value).strip()
                        
                        # Simple validation: if no digits or contains description keywords, set to "-"
                        has_digits = bool(re.search(r'\d', extracted_value_str))
                        has_description_keywords = any(keyword in extracted_value_str for keyword in [
                            'ค่าบริการ', 'ค่าใช้จ่าย', 'โรงพยาบาล', 'รวม', 'ทั้งหมด', 'พยาบาล', 'กรมธรรม์', 'เก็บจาก'
                        ])

                        if not has_digits or has_description_keywords:
                            logger.warning(f"item_no '{extracted_value_str}' is not a valid code, using '-' instead")
                            extracted_value = "-"
                            source_key = None
                        else:
                            source_key = 'item_no' if 'item_no' in item else ('billing_code' if 'billing_code' in item else 'code')
                    else:
                        # No item_no found, use "-"
                        extracted_value = "-"
                        source_key = None
                elif template_field_code == 'billing_code':
                    # Try billing_code, code, item_no
                    extracted_value = item.get('billing_code') or item.get('code') or item.get('item_no')
                    
                    # Validate if it's a real code (not a long description)
                    if extracted_value:
                        extracted_value_str = str(extracted_value).strip()

                        # Simple validation: if no digits or contains description keywords, set to "-"
                        has_digits = bool(re.search(r'\d', extracted_value_str))
                        has_description_keywords = any(keyword in extracted_value_str for keyword in [
                            'ค่าบริการ', 'ค่าใช้จ่าย', 'โรงพยาบาล', 'รวม', 'ทั้งหมด', 'พยาบาล', 'กรมธรรม์', 'เก็บจาก'
                        ])

                        if not has_digits or has_description_keywords:
                            logger.warning(f"billing_code '{extracted_value_str}' is not a valid code, using '-' instead")
                            extracted_value = "-"
                            source_key = None
                        else:
                            source_key = 'billing_code' if 'billing_code' in item else ('code' if 'code' in item else 'item_no')
                    else:
                        # No billing_code found, use "-"
                        extracted_value = "-"
                        source_key = None
                elif template_field_code == 'billing_desc':
                    # Try billing_desc, desc
                    extracted_value = item.get('billing_desc') or item.get('desc')
                    if extracted_value:
                        source_key = 'billing_desc' if 'billing_desc' in item else 'desc'
                elif template_field_code == 'total_amout':
                    extracted_value = (
                        item.get('amount')
                        if item.get('amount') is not None
                        else (item.get('net_amount') if item.get('net_amount') is not None else item.get('total_amout'))
                    )
                    if extracted_value is not None:
                        source_key = (
                            'amount' if 'amount' in item else ('net_amount' if 'net_amount' in item else 'total_amout')
                        )
                elif template_field_code == 'policy_covered':
                    extracted_value = (
                        item.get('policy_covered')
                        if item.get('policy_covered') is not None
                        else (item.get('net_amount') if item.get('net_amount') is not None else item.get('amount'))
                    )
                    if extracted_value is not None:
                        source_key = (
                            'policy_covered' if 'policy_covered' in item else ('net_amount' if 'net_amount' in item else 'amount')
                        )
                elif template_field_code == 'policy_not_covered':
                    extracted_value = item.get('policy_not_covered')
                    if extracted_value is None:
                        extracted_value = '0.00'
                        source_key = None
                elif template_field_code in ['amount', 'discount', 'net_amount', 'item_level']:
                    extracted_value = item.get(template_field_code)
                    if extracted_value is not None:
                        source_key = template_field_code
                
                # Set field value
                if extracted_value is not None:
                    # Special handling for billing_code/item_no: if empty or invalid, use "-"
                    if template_field_code in ['billing_code', 'item_no']:
                        if not extracted_value or extracted_value == "-" or str(extracted_value).strip() == "":
                            field['value'] = "-"
                            field['accuracyRate'] = None
                        else:
                            field['value'] = JSONFormatter._normalize_value(extracted_value, field_type)
                            field['accuracyRate'] = None
                            logger.debug(f"Mapped field {template_field_code} from AI field {source_key}: {extracted_value}")
                    else:
                        field['value'] = JSONFormatter._normalize_value(extracted_value, field_type)
                        field['accuracyRate'] = None
                        logger.debug(f"Mapped field {template_field_code} from AI field {source_key}: {extracted_value}")
                else:
                    # Default values
                    if template_field_code in ['billing_code', 'item_no']:
                        field['value'] = "-"
                    else:
                        field['value'] = '0.00' if field_type == 'decimal' else ("1" if field_type == 'integer' else "-")
                    field['accuracyRate'] = None
                
                field['page'] = "1"
        
        return template_item
    
    @staticmethod
    def _map_item_to_template_strict(item: Dict[str, Any], template_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map extracted item data to template item structure (STRICT MODE)
        Only maps fields that exist in template - does NOT add extra fields from AI response
        Used for order_items to ensure clean structure matching template exactly
        """
        if 'value' in template_item and isinstance(template_item['value'], list):
            template_field_codes = {f.get('code') for f in template_item['value']}
            
            # Only map fields that exist in template
            for field in template_item['value']:
                template_field_code = field.get('code')
                field_type = field.get('type', 'string')
                
                # Try to get value from item using various key names
                extracted_value = None
                source_key = None
                
                # Direct match
                if template_field_code in item:
                    extracted_value = item[template_field_code]
                    source_key = template_field_code
                # Field-specific mappings for order_items
                elif template_field_code == 'item_id':
                    # Try billing_code, code, item_no
                    extracted_value = item.get('billing_code') or item.get('code') or item.get('item_no') or "-"
                    source_key = 'billing_code' if 'billing_code' in item else ('code' if 'code' in item else 'item_no')
                elif template_field_code == 'item_desc':
                    # Try billing_desc, desc
                    extracted_value = item.get('billing_desc') or item.get('desc') or "-"
                    source_key = 'billing_desc' if 'billing_desc' in item else 'desc'
                elif template_field_code == 'item_amont':
                    # Use amount value for item_amont
                    extracted_value = item.get('amount') if item.get('amount') is not None else 0
                    source_key = 'amount'
                elif template_field_code == 'billing_item_no':
                    # Link back to billing code
                    extracted_value = item.get('billing_code') or item.get('code') or item.get('item_no') or "-"
                    source_key = 'billing_code' if 'billing_code' in item else ('code' if 'code' in item else 'item_no')
                elif template_field_code in ['amount', 'discount', 'net_amount']:
                    extracted_value = item.get(template_field_code)
                    if extracted_value is not None:
                        source_key = template_field_code
                
                # Set field value
                if extracted_value is not None:
                    if template_field_code in ['item_id', 'billing_item_no']:
                        if not extracted_value or extracted_value == "-" or str(extracted_value).strip() == "":
                            field['value'] = "-"
                            field['accuracyRate'] = None
                        else:
                            field['value'] = JSONFormatter._normalize_value(extracted_value, field_type)
                            field['accuracyRate'] = None
                    else:
                        field['value'] = JSONFormatter._normalize_value(extracted_value, field_type)
                        field['accuracyRate'] = None
                else:
                    # Default values
                    if template_field_code in ['item_id', 'item_desc', 'billing_item_no']:
                        field['value'] = "-"
                    else:
                        field['value'] = '0.00' if field_type == 'decimal' else "-"
                    field['accuracyRate'] = None
                
                field['page'] = "1"
        
        return template_item
    
    @staticmethod
    def _normalize_value(val: Any, ftype: str) -> Any:
        """Normalize value by type"""
        if val is None:
            return '-'
        if isinstance(val, str) and val.strip() in {'', 'null', 'none', 'Null', 'None', 'N/A', 'n/a'}:
            return '-'
        
        if ftype == 'date':
            # Date normalization to YYYY-MM-DD
            try:
                from datetime import datetime as _dt
                s = str(val).strip()
                fmts = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']
                for f in fmts:
                    try:
                        d = _dt.strptime(s, f)
                        return d.strftime('%Y-%m-%d')
                    except:
                        pass
            except:
                pass
            return '-'
        elif ftype == 'decimal':
            # Decimal normalization
            try:
                import re as _re
                s = str(val).strip().replace('฿', '').replace('THB', '').replace('บาท', '').replace('Baht', '')
                s = s.replace('−', '-').replace(' ', '').replace(',', '')
                s = _re.sub(r'[^0-9\.-]', '', s)
                if s.count('.') > 1:
                    parts = s.split('.')
                    s = ''.join(parts[:-1]) + '.' + parts[-1]
                f = float(s)
                return f"{f:.2f}"
            except:
                return val
        elif ftype == 'integer':
            try:
                return str(int(str(val).replace(',', '').strip()))
            except:
                return val
        
        return val
    
    @staticmethod
    def _normalize_all_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively normalize all values in the structure"""
        if isinstance(data, dict):
            return {k: JSONFormatter._normalize_all_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [JSONFormatter._normalize_all_values(item) for item in data]
        else:
            return data
