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
        
        # Initialize OCR Manager
        self.ocr_manager = MultiOCRManager(self.config)
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0
        }
    
    def process_document(self, image_path: str, template: str = "medical_receipt") -> Dict[str, Any]:
        """
        Process document from image file
        Delegates to OCR + extraction
        """
        import time
        start_time = time.time()
        
        try:
            # 1. Perform OCR
            logger.info(f"Processing image: {image_path} with template: {template}")
            ocr_result = self.ocr_manager.extract_text(image_path)
            
            if not ocr_result.get('success', False):
                return {
                    'success': False,
                    'error': f"OCR failed: {ocr_result.get('error')}"
                }
                
            ocr_text = ocr_result.get('text', '')
            
            # Prepare OCR results format expected by simple_extractor
            # (Creating a mock result structure since we have raw text)
            ocr_results = [{
                'text': ocr_text,
                'confidence': 0.99,
                'bbox': []  # Dummy bbox
            }]
            
            # 2. AI Extraction
            simple_data = self.simple_extractor.extract_simple(
                ocr_results, 
                save_request=True, 
                template=template
            )
            
            # 3. Format Data
            # Load template config to get form info
            template_config = self.template_manager.get_template(template)
            
            metadata = {
                "source_length": len(ocr_text),
                "processing_time": time.time() - start_time,
                "detected_language": "th",
                "form_id": template_config.get('form_id') if template_config else template,
                "document_type": template_config.get('document_type') if template_config else template
            }
            
            formatted_data = self.json_formatter.format_to_medical_receipt_json(
                simple_data,
                metadata,
                template_config=template_config
            )
            
            self.stats['successful'] += 1
            return {
                'success': True,
                'data': formatted_data,
                'timing': {
                    'total_time': time.time() - start_time
                }
            }

        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
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
        """Create simplified prompt for AI extraction (Revised)"""
        top_keys = ', '.join(template_keys.get('top_level', []))
        
        prompt = f"""Extract data from the following OCR text and return as JSON.

OCR Text:
{ocr_text}

TARGET JSON FORMAT:
{{
  "{'", "'.join(template_keys.get('top_level', []))}",
  "billing_items": [
    {{
      "code": "string (e.g. 1.1.1, 1.2.1)",
      "description": "string",
      "amount": "number or string",
      "discount": "number or string",
      "net_amount": "number or string"
    }}
  ]
}}

RULES:
1. Extract ALL line items found in the text into "billing_items".
2. Copy "code" and "description" EXACTLY as they appear in the text.
3. Do NOT try to categorize items (e.g. Medicine vs Service) yet. Just extract them all.
4. Do NOT create nested structures (L1/L2/L3). Keep it a FLAT list.
5. Ignore summary lines like "Total", "Net Total", "รวมเงิน".
6. If a value is missing, use null.

Return ONLY raw JSON. No Markdown formatting.
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
        """Build simplified guidance for AI"""
        return (
            "You are an expert OCR data extractor for Thai medical receipts.\n"
            "Your task is to extract data precisely into JSON format.\n"
            "Focus on capturing every single line item correctly."
        )

    def _parse_ai_json_response(self, content: str, template_keys: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Simplified JSON parser - Handles flat list from AI and applies business logic
        """
        # 1. Parse JSON safely
        json_obj = self._safe_json_parse(content)
        if not json_obj:
            logger.error("No valid JSON found in AI response")
            return self._create_empty_result(template_keys)
        
        # 2. Extract Top-Level Fields
        extracted = self._extract_top_level_fields(json_obj, template_keys)
        
        # 3. Extract and Process Items
        raw_items = json_obj.get('billing_items', [])
        if not isinstance(raw_items, list):
            # Handle case where AI returns single dict instead of list
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            else:
                raw_items = []
            
        # Filter invalid items & Normalize
        valid_items = []
        for item in raw_items:
            if not isinstance(item, dict): continue
            
            # Normalize fields
            norm_item = self._normalize_item(item)
            
            # Skip summary lines (Total, Net Total, etc.)
            if self._is_summary_line(norm_item):
                continue
                
            valid_items.append(norm_item)
            
        # 4. Separate Order Items (Medicine) vs Billing Items (Services)
        billing_items, order_items = self._categorize_items(valid_items)
        
        extracted['billing_items'] = billing_items
        extracted['_order_items_data'] = order_items # Internal use for formatter
        
        logger.info(f"✅ Extracted: {len(billing_items)} billing items, {len(order_items)} order items")
        
        return extracted

    def _safe_json_parse(self, content: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON block
            import re
            match = re.search(r'\{[\s\S]*\}', content)
            if match:
                try:
                    return json.loads(match.group(0))
                except:
                    pass
            return None

    def _extract_top_level_fields(self, json_obj: Dict[str, Any], template_keys: Dict[str, List[str]]) -> Dict[str, Any]:
        extracted = {}
        for key in template_keys.get('top_level', []):
            # Try exact match then variations
            if key in json_obj:
                extracted[key] = json_obj[key]
            else:
                for var in self._get_key_variations(key):
                    if var in json_obj:
                        extracted[key] = json_obj[var]
                        break
        return extracted

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize keys
        code = str(item.get('code') or item.get('billing_code') or item.get('item_no') or '-').strip()
        desc = str(item.get('description') or item.get('billing_desc') or item.get('desc') or '').strip()
        
        # Fix common OCR errors in code
        if code in ['-', 'null', 'None', 'N/A']: code = ''
        
        # Ensure amounts are present
        def get_val(k): return item.get(k)
        
        return {
            'billing_code': code,
            'billing_desc': desc,
            'amount': get_val('amount'),
            'discount': get_val('discount'),
            'net_amount': get_val('net_amount'),
            'original': item # Keep original for debug
        }

    def _is_summary_line(self, item: Dict[str, Any]) -> bool:
        desc = item['billing_desc'].lower()
        code = item['billing_code'].lower()
        keywords = ['total', 'net total', 'summary', 'amount due', 'รวมเงิน', 'ยอดรวม', 'สุทธิ', 'รวมทั้งสิ้น']
        
        # Check if description contains keywords EXACTLY or starts with them
        for kw in keywords:
            if desc == kw or desc.startswith(kw + ' ') or desc.startswith(kw + ':'):
                return True
            if code == kw:
                return True
        return False

    def _categorize_items(self, items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        billing_items = []
        order_items = []
        
        # Medicine keywords - items containing these are "Order Items"
        medicine_keywords = [
            'ยา', 'tablet', 'capsule', 'inj', 'mg', 'ml', 'mcg', 'gram', 
            'tab', 'cap', 'syr', 'susp', 'oint', 'cream', 'gel'
        ]
        
        # Service keywords - items containing these are definitely "Billing Items" (override medicine)
        service_keywords = [
            'ค่าบริการ', 'ค่าธรรมเนียม', 'ค่าตรวจ', 'ค่าห้อง', 'ค่าอาหาร', 
            'service', 'fee', 'room', 'food', 'nursing', 'doctor'
        ]
        
        for item in items:
            code = item['billing_code']
            desc = item['billing_desc'].lower()
            
            is_medicine = False
            is_service = False
            
            # Check service keywords first (Stronger rule)
            if any(kw in desc for kw in service_keywords):
                is_service = True
            elif any(kw in desc for kw in medicine_keywords):
                is_medicine = True
                
            # Check code patterns
            # e.g. 1.1.1 is usually medicine category, 1.1.1(1) is medicine item
            # If code has parentheses AND is medicine -> Order Item
            has_parentheses = '(' in code and ')' in code
            
            if is_service:
                billing_items.append(item)
            elif is_medicine:
                order_items.append(item)
            else:
                # Default to Billing Item if unsure
                billing_items.append(item)
                
        return billing_items, order_items

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
        import copy
        
        # Generate transaction_no if not provided
        if not transaction_no:
            import time
            transaction_no = f"TX{int(time.time() * 1000)}"
        
        # Get document_code/type from template API
        if not document_code and template_config:
            document_code = template_config.get('form_id')
        if not document_code:
            document_code = f"CM{int(time.time() * 1000)}"
            
        document_type = "Detail"
        if template_config:
            document_type = template_config.get('document_type', "Detail")
        
        # Get Template Structure
        template_structure = None
        if template_config:
            if 'Template_json' in template_config:
                t_json = template_config['Template_json']
                if isinstance(t_json, str):
                    try:
                        template_structure = json.loads(t_json)
                    except:
                        pass
                else:
                    template_structure = t_json
            elif 'template_structure' in template_config:
                template_structure = copy.deepcopy(template_config['template_structure'])
        
        if not template_structure:
            logger.error("Template structure unavailable")
            raise RuntimeError("Template_json not available; cannot format output.")

        # Fill in the template
        if 'documents' in template_structure and len(template_structure['documents']) > 0:
            document = template_structure['documents'][0]
            
            # Set metadata
            document['document_code'] = document_code
            document['document_type'] = document_type
            document['page'] = "1"
            document['total_page'] = "1"
            
            # Prepare simple data lookups
            simple = dict(simple_data or {})
            
            if 'document_info' in document:
                for field in document['document_info']:
                    field_code = field.get('code')
                    field_type = field.get('type', 'string')
                    
                    # 1. Handle Billing Items (Service Fees)
                    if field_code == 'billing_items' and field_type == 'array':
                        items = simple.get('billing_items', [])
                        field['value'] = JSONFormatter._map_items_to_template(items, field)
                        field['accuracyRate'] = None
                        
                    # 2. Handle Order Items (Medicines)
                    elif field_code == 'order_items' and field_type == 'array':
                        items = simple.get('_order_items_data', [])
                        field['value'] = JSONFormatter._map_items_to_template(items, field)
                        field['accuracyRate'] = None
                        
                    # 3. Handle Top-level Fields
                    else:
                        value = simple.get(field_code)
                        if value is not None:
                            field['value'] = JSONFormatter._normalize_value(value, field_type)
                        else:
                            field['value'] = "-"
                        field['accuracyRate'] = None
        
        # Set transaction_no at root
        template_structure['transaction_no'] = transaction_no
        
        return JSONFormatter._normalize_all_values(template_structure)

    @staticmethod
    def _map_items_to_template(items: List[Dict[str, Any]], template_field: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map a list of flat items to the template structure.
        Uses the first item in the template array as the schema.
        """
        import copy
        
        if not items:
            return []
            
        # Get the schema (template row)
        template_rows = template_field.get('value', [])
        if not template_rows or not isinstance(template_rows, list):
            logger.warning(f"No template row definition found for {template_field.get('code')}")
            return []
            
        schema_row = template_rows[0] # Use first row as schema
        result_rows = []
        
        for item in items:
            # Create a new row from schema
            new_row = copy.deepcopy(schema_row)
            
            # Fill the row with item data
            JSONFormatter._fill_template_row(new_row, item)
            
            result_rows.append(new_row)
            
        return result_rows

    @staticmethod
    def _fill_template_row(template_row: Dict[str, Any], item_data: Dict[str, Any]):
        """
        Recursively fill a template row with item data.
        """
        # If row has 'value' (it's a wrapper object like in billing_items)
        if 'value' in template_row and isinstance(template_row['value'], list):
            for field in template_row['value']:
                JSONFormatter._fill_field(field, item_data)
        # If row is just a dict of fields (some templates)
        elif isinstance(template_row, dict):
             JSONFormatter._fill_field(template_row, item_data)

    @staticmethod
    def _fill_field(field: Dict[str, Any], item_data: Dict[str, Any]):
        """
        Fill a single field with data, handling mapping logic.
        """
        code = field.get('code')
        ftype = field.get('type', 'string')
        
        # Recursive handle for nested arrays (like grouporder_items)
        if ftype == 'array' and 'value' in field:
             # For now, we are flattening everything, so nested arrays stay empty
             # or we could map specific children if we had logic for it.
             field['value'] = []
             return

        # Map keys
        # Prioritize exact match, then common mappings
        val = None
        
        # Direct match
        if code in item_data:
            val = item_data[code]
        
        # Mapping Logic
        elif code in ['billing_code', 'item_id', 'billing_item_no', 'code']:
            val = item_data.get('billing_code') or item_data.get('code')
        elif code in ['billing_desc', 'item_desc', 'desc', 'description']:
            val = item_data.get('billing_desc') or item_data.get('description')
        elif code in ['amount', 'item_amont', 'total_amout']:
            val = item_data.get('amount')
        elif code in ['discount']:
            val = item_data.get('discount')
        elif code in ['net_amount', 'policy_covered']:
            val = item_data.get('net_amount')
        elif code == 'item_level':
            val = item_data.get('item_level', 1) # Default level 1
            
        # Set value if found
        if val is not None:
            field['value'] = JSONFormatter._normalize_value(val, ftype)
        else:
            # Default empty values
            if ftype == 'decimal': field['value'] = "0.00"
            elif ftype == 'integer': field['value'] = "0"
            else: field['value'] = "-"
            
        field['accuracyRate'] = None
        field['page'] = "1"

    @staticmethod
    def _normalize_value(val: Any, ftype: str) -> Any:
        """Normalize value by type"""
        if val is None:
            return '-'
        if isinstance(val, str) and val.strip() in {'', 'null', 'none', 'Null', 'None', 'N/A', 'n/a'}:
            return '-'
        
        s_val = str(val).strip()
        
        if ftype == 'date':
            # Date normalization to YYYY-MM-DD
            try:
                from datetime import datetime as _dt
                fmts = ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%m-%d-%Y']
                for f in fmts:
                    try:
                        d = _dt.strptime(s_val, f)
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
                # Remove currency symbols and commas
                s = s_val.replace('฿', '').replace('THB', '').replace('บาท', '').replace('Baht', '')
                s = s.replace('−', '-').replace(' ', '').replace(',', '')
                # Keep only digits, dot, minus
                s = _re.sub(r'[^0-9\.-]', '', s)
                if not s: return "0.00"
                f = float(s)
                return f"{f:.2f}"
            except:
                return "0.00"
        elif ftype == 'integer':
            try:
                # Remove non-digits
                import re as _re
                s = _re.sub(r'[^0-9]', '', s_val)
                if not s: return "0"
                return str(int(s))
            except:
                return "0"
        
        return s_val
    
    @staticmethod
    def _normalize_all_values(data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively normalize all values in the structure"""
        if isinstance(data, dict):
            return {k: JSONFormatter._normalize_all_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [JSONFormatter._normalize_all_values(item) for item in data]
        else:
            return data
