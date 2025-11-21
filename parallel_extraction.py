"""
Parallel Extraction - Extract multiple receipts concurrently
แยก OCR text เป็นหลาย receipts แล้วส่งให้ AI พร้อมกัน (parallel)
"""

import asyncio
import aiohttp
import json
import os
import sys
import io
import time
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ai_simple_extraction import SimpleAIExtractor
from template_api_manager import TemplateAPIManager
from log_manager import setup_logging

# Fix console encoding for emojis on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

logger = logging.getLogger(__name__)


class ReceiptSplitter:
    """แยก OCR text ที่มีหลาย receipts เป็น receipts แยกกัน"""
    
    @staticmethod
    def split_by_page_markers(ocr_text: str) -> List[Dict[str, Any]]:
        """
        แยก OCR text โดยใช้ page markers (หน้าที่ X)
        แต่ละ receipt มี 2 หน้า (Original + Copy)

        Returns:
            List of receipts, each with {receipt_id, receipt_number, pages, ocr_text, start_page, end_page}
        """
        lines = ocr_text.split('\n')
        page_markers = []

        # หาตำแหน่งของทุก page marker
        for i, line in enumerate(lines):
            if line.startswith('หน้าที่'):
                try:
                    page_num = int(line.split()[1])
                    page_markers.append((i, page_num))
                except (IndexError, ValueError):
                    continue

        receipts = []
        receipt_counter = 0

        # จัดกลุ่ม pages เป็นคู่ (Original + Copy)
        for i in range(0, len(page_markers), 2):
            if i + 1 < len(page_markers):
                start_line = page_markers[i][0]
                end_line = page_markers[i + 1][0] - 1  # จนถึงก่อนหน้าถัดไป
                start_page = page_markers[i][1]
                end_page = page_markers[i + 1][1]

                # ตัด OCR text สำหรับ receipt นี้
                receipt_lines = lines[start_line:end_line + 1]
                receipt_text = '\n'.join(receipt_lines)

                # หา receipt number ใน receipt นี้ (เฉพาะเลขที่ขึ้นต้นด้วย 228)
                receipt_number = None
                for line in receipt_lines:
                    if 'Receipt Number' in line or 'Receipt Numoer' in line or 'Receipt Numbel' in line:
                        matches = re.findall(r'\b(228\d{7})\b', line)
                        if matches:
                            receipt_number = matches[0]  # ใช้ตัวแรกที่พบ
                            break

                # สร้าง receipt ID
                receipt_id = f"receipt_{receipt_counter:03d}"

                receipts.append({
                    'receipt_id': receipt_id,
                    'receipt_number': receipt_number,  # อาจเป็น None ถ้าไม่พบ
                    'pages': 2,  # แต่ละ receipt มี 2 หน้า
                    'ocr_text': receipt_text,
                    'start_page': start_page,
                    'end_page': end_page
                })

                receipt_counter += 1

        logger.info(f"📋 Split OCR text into {len(receipts)} receipts")
        return receipts
    
    @staticmethod
    def extract_first_receipt_only(ocr_text: str) -> str:
        """
        แยกเฉพาะ receipt แรก (2 หน้า: Original + Copy)
        สำหรับ single document extraction
        """
        lines = ocr_text.split('\n')
        page_markers = []
        
        # หาตำแหน่งของแต่ละหน้า
        for i, line in enumerate(lines):
            if line.startswith('หน้าที่'):
                page_number = int(line.split()[1])
                page_markers.append((i, page_number))
        
        # ตัดก่อนหน้าที่ 3 (เก็บแค่หน้า 1-2)
        if len(page_markers) >= 3:
            end_line = page_markers[2][0]
            return '\n'.join(lines[:end_line])
        
        return ocr_text


class BatchReceiptExtractor:
    """Extract receipts using batch processing (recommended approach)"""

    def __init__(self, config):
        self.config = config
        self.ai_extractor = SimpleAIExtractor(config)

    def extract_batch(self, receipts: List[Dict[str, Any]], form_id: str = None) -> List[Dict[str, Any]]:
        """
        Extract receipts in batches to avoid API overload
        
        Args:
            receipts: List of receipt data
            form_id: Form ID to use for extraction (e.g., 'HL0000050', 'HL0000053')
        """
        parallel_config = self.config.get('ai_extraction', {}).get('parallel_processing', {})
        batch_size = parallel_config.get('batch_size', 5)
        
        # Use timeout from ai_extraction.api.timeout (default 300s) instead of timeout_per_request
        ai_api_config = self.config.get('ai_extraction', {}).get('api', {})
        timeout_per_request = parallel_config.get('timeout_per_request') or ai_api_config.get('timeout', 300)

        all_results = []
        total_receipts = len(receipts)

        logger.info(f"📦 Starting batch extraction for {total_receipts} receipts (batch size: {batch_size})")

        # Process in batches
        for batch_start in range(0, total_receipts, batch_size):
            batch_end = min(batch_start + batch_size, total_receipts)
            batch_receipts = receipts[batch_start:batch_end]
            batch_num = (batch_start // batch_size) + 1
            total_batches = (total_receipts + batch_size - 1) // batch_size

            logger.info(f"📦 Processing Batch {batch_num}/{total_batches}: receipts {batch_start}-{batch_end-1}")

            batch_results = self._extract_single_batch(batch_receipts, batch_num, timeout_per_request, form_id)
            all_results.extend(batch_results)

            # Progress update
            completed = len(all_results)
            successful = sum(1 for r in all_results if r.get('success'))
            logger.info(f"📊 Progress: {completed}/{total_receipts} receipts processed, {successful} successful")

        return all_results

    def _extract_single_batch(self, receipts: List[Dict[str, Any]], batch_num: int, timeout: float, form_id: str = None) -> List[Dict[str, Any]]:
        """
        Extract a single batch of receipts sequentially (not parallel)
        
        Args:
            receipts: List of receipt data
            batch_num: Batch number for logging
            timeout: Timeout in seconds
            form_id: Form ID to use for extraction (e.g., 'HL0000050', 'HL0000053')
        """
        results = []
        
        # Default form_id if not provided
        if not form_id:
            form_id = 'HL0000050'  # Default to Receipt-Bill
            logger.warning(f"⚠️ No form_id provided, using default: {form_id}")

        for receipt_data in receipts:
            receipt_id = receipt_data.get('receipt_id', 'unknown')
            logger.info(f"🔄 [{receipt_id}] Starting extraction (Batch {batch_num}, form_id: {form_id})...")

            try:
                # Extract using AI with timeout
                start_time = time.time()

                # Use ThreadPoolExecutor to run sync function with timeout
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self.ai_extractor.extract_simple,
                        [{'text': receipt_data['ocr_text']}],  # Format as expected by SimpleAIExtractor
                        True,   # save_request
                        form_id  # Use provided form_id instead of hardcoded 'medical_receipt'
                    )

                    try:
                        result = future.result(timeout=timeout)
                        processing_time = time.time() - start_time

                        # Check if result is valid (extract_simple returns dict with data, not wrapper with 'success')
                        # Valid result should have at least some extracted fields
                        if result and isinstance(result, dict):
                            # Check if extraction was successful by looking for key fields
                            has_data = (
                                result.get('hospital_name') or 
                                result.get('billing_items') or 
                                result.get('gross_amount') or
                                len(result) > 0  # At least some data was extracted
                            )
                            
                            if has_data:
                                billing_items_count = len(result.get('billing_items', []))
                                logger.info(f"✅ [{receipt_id}] Extracted {billing_items_count} items in {processing_time:.2f}s")
                                results.append({
                                    'success': True,
                                    'receipt_id': receipt_id,
                                    'receipt_number': result.get('receipt_number') or result.get('invoice_no'),
                                    'data': result,
                                    'extraction_time': processing_time
                                })
                            else:
                                logger.error(f"❌ [{receipt_id}] Extraction returned empty result")
                                results.append({
                                    'success': False,
                                    'receipt_id': receipt_id,
                                    'error': 'Extraction returned empty result'
                                })
                        else:
                            logger.error(f"❌ [{receipt_id}] Extraction failed: invalid result type")
                            results.append({
                                'success': False,
                                'receipt_id': receipt_id,
                                'error': 'Extraction failed: invalid result'
                            })

                    except concurrent.futures.TimeoutError:
                        logger.error(f"⏱️ [{receipt_id}] Timeout after {timeout}s")
                        results.append({
                            'success': False,
                            'receipt_id': receipt_id,
                            'error': f'Timeout after {timeout}s'
                        })

            except Exception as e:
                logger.error(f"❌ [{receipt_id}] Exception: {str(e)}")
                results.append({
                    'success': False,
                    'receipt_id': receipt_id,
                    'error': str(e)
                })

        return results

    def extract_all_receipts_sync(self, receipts: List[Dict[str, Any]], save_request: bool = True, form_id: str = None) -> List[Dict[str, Any]]:
        """
        Compatibility method that calls extract_batch
        
        Args:
            receipts: List of receipt data
            save_request: Whether to save requests (for compatibility, not used)
            form_id: Form ID to use for extraction (e.g., 'HL0000050', 'HL0000053')
        """
        return self.extract_batch(receipts, form_id)


class ParallelReceiptExtractor:
    """Extract multiple receipts in parallel using async"""
    
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
        self.auth_token = self.api_config.get('auth_token')

        # Parallel settings
        self.parallel_config = self.ai_config.get('parallel_processing', {})
        self.max_concurrent = self.parallel_config.get('max_concurrent_requests', 10)
        self.batch_size = self.parallel_config.get('batch_size', 5)

        # Template manager and Template_json keys
        self.template_manager = TemplateAPIManager(config)
        self.template_form_id_mapping = config.get('templates', {}).get('form_id_mapping', {})
        self.template_structure = None
        try:
            default_form_id = self.template_form_id_mapping.get('medical_receipt')
            if default_form_id:
                tpl = self.template_manager.get_template(default_form_id)
                self.template_structure = tpl.get('template_structure') if tpl else None
        except Exception:
            self.template_structure = None
        
        logger.info(f"Parallel extractor initialized: max_concurrent={self.max_concurrent}, batch_size={self.batch_size}")
    
    async def extract_receipt_async(self, 
                                   receipt: Dict[str, Any], 
                                   session: aiohttp.ClientSession,
                                   save_request: bool = True) -> Dict[str, Any]:
        """
        Extract single receipt using async HTTP request
        
        Args:
            receipt: Receipt data with OCR text
            session: aiohttp session
            save_request: Save request/response for debugging
        
        Returns:
            Extracted data for this receipt
        """
        try:
            receipt_id = receipt['receipt_id']
            receipt_number = receipt['receipt_number']
            
            logger.info(f"🔍 [{receipt_id}] Starting extraction for receipt {receipt_number}")
            
            # Create prompt for this receipt
            prompt = self._create_receipt_prompt(receipt['ocr_text'])
            
            # Build request payload
            template_keys_guidance = self._build_template_keys_guidance(self.template_structure)
            payload = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'system',
                        'content': template_keys_guidance
                    },
                    {
                        'role': 'system',
                        'content': 'You are an EXPERT at extracting structured data from Thai medical receipts with 100% accuracy.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'seed': self.seed,
                'stop': self.stop,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'max_tokens': self.max_tokens,
                'frequency_penalty': self.frequency_penalty,
                'presence_penalty': self.presence_penalty
            }
            
            # Save request
            request_id = None
            if save_request:
                request_id = self._save_request(receipt_id, payload, receipt)
            
            # Call AI API (async)
            start_time = time.time()
            async with session.post(
                self.endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                elapsed_time = time.time() - start_time
                
                if response.status == 200:
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    
                    # Save response
                    if save_request and request_id:
                        self._save_response(request_id, result, content, receipt_id)
                    
                    # Parse response
                    parsed = self._parse_response(content, receipt)
                    parsed['extraction_time'] = elapsed_time
                    
                    logger.info(f"✅ [{receipt_id}] Extracted {len(parsed.get('billing_items', []))} items in {elapsed_time:.2f}s")
                    
                    return {
                        'success': True,
                        'receipt_id': receipt_id,
                        'receipt_number': receipt_number,
                        'data': parsed
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"❌ [{receipt_id}] API error {response.status}: {error_text[:200]}")
                    
                    return {
                        'success': False,
                        'receipt_id': receipt_id,
                        'receipt_number': receipt_number,
                        'error': f"HTTP {response.status}: {error_text[:200]}"
                    }
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ [{receipt['receipt_id']}] Timeout after {self.timeout}s")
            return {
                'success': False,
                'receipt_id': receipt['receipt_id'],
                'receipt_number': receipt['receipt_number'],
                'error': f"Timeout after {self.timeout}s"
            }
        
        except Exception as e:
            logger.error(f"❌ [{receipt['receipt_id']}] Extraction error: {e}")
            return {
                'success': False,
                'receipt_id': receipt['receipt_id'],
                'receipt_number': receipt['receipt_number'],
                'error': str(e)
            }
    
    async def extract_all_receipts_async(self, 
                                        receipts: List[Dict[str, Any]], 
                                        save_request: bool = True) -> List[Dict[str, Any]]:
        """
        Extract all receipts in parallel using async
        
        Args:
            receipts: List of receipts to extract
            save_request: Save requests/responses
        
        Returns:
            List of extraction results
        """
        logger.info(f"🚀 Starting parallel extraction for {len(receipts)} receipts")
        logger.info(f"   Max concurrent: {self.max_concurrent}")
        logger.info(f"   Batch size: {self.batch_size}")
        
        # Create aiohttp session
        connector = aiohttp.TCPConnector(limit=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        # Build default headers
        default_headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            default_headers['Authorization'] = f"Bearer {self.auth_token}"

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers=default_headers
        ) as session:
            
            # Create tasks for all receipts
            tasks = [
                self.extract_receipt_async(receipt, session, save_request)
                for receipt in receipts
            ]
            
            # Execute all tasks concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Handle exceptions
            final_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Receipt {i}: {result}")
                    final_results.append({
                        'success': False,
                        'receipt_id': receipts[i]['receipt_id'],
                        'receipt_number': receipts[i]['receipt_number'],
                        'error': str(result)
                    })
                else:
                    final_results.append(result)
            
            # Summary
            successful = sum(1 for r in final_results if r.get('success'))
            failed = len(final_results) - successful
            
            logger.info(f"✅ Parallel extraction completed in {total_time:.2f}s")
            logger.info(f"   Total: {len(final_results)} receipts")
            logger.info(f"   Successful: {successful}")
            logger.info(f"   Failed: {failed}")
            logger.info(f"   Average time per receipt: {total_time/len(receipts):.2f}s")
            
            return final_results
    
    def extract_all_receipts_sync(self, 
                                 receipts: List[Dict[str, Any]], 
                                 save_request: bool = True) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for extract_all_receipts_async
        
        Args:
            receipts: List of receipts
            save_request: Save requests/responses
        
        Returns:
            List of extraction results
        """
        return asyncio.run(self.extract_all_receipts_async(receipts, save_request))
    
    def _create_receipt_prompt(self, ocr_text: str) -> str:
        """Create prompt for single receipt extraction"""
        # Determine billing item column names from Template_json (fallback to defaults)
        billing_field_codes = ['billing_code', 'billing_desc', 'amount', 'discount', 'net_amount']
        try:
            ts = self.template_structure
            if ts and isinstance(ts, dict):
                doc_info = (
                    ts.get('output_format', {})
                    .get('extracted_data', {})
                    .get('document_info')
                )
                if not doc_info and 'documents' in ts:
                    docs = ts.get('documents')
                    if isinstance(docs, list) and docs:
                        doc_info = docs[0].get('document_info')
                if isinstance(doc_info, list):
                    billing_item = next((e for e in doc_info if e.get('code') == 'billing_items'), None)
                    if billing_item:
                        fields = billing_item.get('value', [])
                        if fields:
                            billing_fields = fields[0].get('value', [])
                            billing_field_codes = [f.get('code') for f in billing_fields if f.get('code')]
        except Exception:
            pass

        prompt = f"""You are an EXPERT at extracting structured data from Thai medical receipts. Extract data from this ONE receipt.

===== OCR TEXT FROM RECEIPT =====
{ocr_text}
===== END OCR TEXT =====

YOUR TASK:
Extract the following information ACCURATELY and COMPLETELY.

⚠️ CRITICAL OUTPUT RULES:
❌ NO markdown formatting
❌ NO commentary or explanations
❌ NO questions or summaries
✅ OUTPUT ONLY the extracted data

EXTRACT (plain text format):
HOSPITAL_NAME: [hospital name]
RECEIPT_NUMBER: [receipt number]
CUSTOMER_NUMBER: [customer number if available]
RECEIPT_DATE: [date in DD/MM/YYYY]
TOTAL_AMOUNT: [total amount with commas]

BILLING_ITEMS:
[{billing_field_codes[0]}] | [{billing_field_codes[1]}] | [{billing_field_codes[2]}] | [{billing_field_codes[3]}] | [{billing_field_codes[4]}]
[{billing_field_codes[0]}] | [{billing_field_codes[1]}] | [{billing_field_codes[2]}] | [{billing_field_codes[3]}] | [{billing_field_codes[4]}]
...

IMPORTANT:
- Extract ALL billing items (ทุกรายการ)
- Use pipe | to separate fields
- Include commas in amounts (e.g., 46,137.80)
- Be accurate with numbers

OUTPUT FORMAT (NO other text):
HOSPITAL_NAME: [value]
RECEIPT_NUMBER: [value]
CUSTOMER_NUMBER: [value]
RECEIPT_DATE: [value]
TOTAL_AMOUNT: [value]

BILLING_ITEMS:
[{billing_field_codes[0]}] | [{billing_field_codes[1]}] | [{billing_field_codes[2]}] | [{billing_field_codes[3]}] | [{billing_field_codes[4]}]
[{billing_field_codes[0]}] | [{billing_field_codes[1]}] | [{billing_field_codes[2]}] | [{billing_field_codes[3]}] | [{billing_field_codes[4]}]
...

NOW EXTRACT:"""
        
        return prompt

    def _build_template_keys_guidance(self, template_structure: Optional[Dict[str, Any]]) -> str:
        """Create compact guidance string listing Template_json keys to enforce consistent field names."""
        try:
            if not template_structure:
                return (
                    "IMPORTANT: Use these Template_json field codes for output keys: "
                    "hospital_name, hn, an, gross_amount, admission_date, discharge_date, billing_items; "
                    "billing_items columns: billing_code, billing_desc, amount, discount, net_amount."
                )

            doc_info = None
            if isinstance(template_structure, dict):
                doc_info = (
                    template_structure.get('output_format', {})
                    .get('extracted_data', {})
                    .get('document_info')
                )
                if not doc_info:
                    docs = template_structure.get('documents')
                    if isinstance(docs, list) and docs:
                        doc_info = docs[0].get('document_info')

            top_level_codes = []
            billing_field_codes = ['billing_code', 'billing_desc', 'amount', 'discount', 'net_amount']

            if isinstance(doc_info, list):
                for entry in doc_info:
                    code = entry.get('code')
                    if code and code != 'billing_items':
                        top_level_codes.append(code)
                    elif code == 'billing_items':
                        try:
                            billing_item = entry.get('value', [])[0]
                            fields = billing_item.get('value', [])
                            billing_field_codes = [f.get('code') for f in fields if f.get('code')]
                        except Exception:
                            pass

            return (
                f"IMPORTANT: Use these Template_json field codes for output keys exactly: "
                f"{', '.join(top_level_codes)}. "
                f"For billing_items, use columns: {', '.join(billing_field_codes)}. "
                f"Return only extracted data, no explanations."
            )
        except Exception:
            return (
                "IMPORTANT: Use these Template_json field codes for output keys: "
                "hospital_name, hn, an, gross_amount, admission_date, discharge_date, billing_items; "
                "billing_items columns: billing_code, billing_desc, amount, discount, net_amount."
            )
    
    def _parse_response(self, content: str, receipt: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response into structured data"""
        
        data = {
            'hospital_name': None,
            'receipt_number': receipt['receipt_number'],  # From split logic
            'customer_number': None,
            'receipt_date': None,
            'total_amount': None,
            'billing_items': [],
            'pages': receipt.get('pages', 2),
            'start_page': receipt.get('start_page'),
            'end_page': receipt.get('end_page')
        }
        
        lines = content.strip().split('\n')
        in_billing_section = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse fields
            if line.startswith('HOSPITAL_NAME:'):
                data['hospital_name'] = line.split(':', 1)[1].strip()
            elif line.startswith('RECEIPT_NUMBER:'):
                data['receipt_number'] = line.split(':', 1)[1].strip()
            elif line.startswith('CUSTOMER_NUMBER:'):
                data['customer_number'] = line.split(':', 1)[1].strip()
            elif line.startswith('RECEIPT_DATE:'):
                data['receipt_date'] = line.split(':', 1)[1].strip()
            elif line.startswith('TOTAL_AMOUNT:'):
                data['total_amount'] = line.split(':', 1)[1].strip()
            elif 'BILLING_ITEMS' in line.upper():
                in_billing_section = True
            elif in_billing_section and '|' in line:
                # Parse billing item
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2:
                    data['billing_items'].append({
                        'description': parts[0],
                        'amount': parts[1]
                    })
        
        return data
    
    def _save_request(self, receipt_id: str, payload: Dict[str, Any], receipt: Dict[str, Any]) -> str:
        """Save request for debugging"""
        request_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + receipt_id
        
        debug_dir = './output/ai_debug/parallel_requests'
        os.makedirs(debug_dir, exist_ok=True)
        
        request_file = os.path.join(debug_dir, f"request_{request_id}.json")
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump({
                'request_id': request_id,
                'receipt_id': receipt_id,
                'receipt_number': receipt.get('receipt_number'),
                'timestamp': datetime.now().isoformat(),
                'payload': payload
            }, f, indent=2, ensure_ascii=False)
        
        return request_id
    
    def _save_response(self, request_id: str, result: Dict[str, Any], content: str, receipt_id: str):
        """Save response for debugging"""
        debug_dir = './output/ai_debug/parallel_responses'
        os.makedirs(debug_dir, exist_ok=True)
        
        response_file = os.path.join(debug_dir, f"response_{request_id}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump({
                'request_id': request_id,
                'receipt_id': receipt_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'full_response': result,
                'extracted_content': content
            }, f, indent=2, ensure_ascii=False)


def extract_multiple_receipts_from_file(ocr_file_path: str, config_path: str = 'config.json') -> Dict[str, Any]:
    """
    Extract multiple receipts from a single OCR file (with 88 pages)
    
    Args:
        ocr_file_path: Path to request JSON file (e.g., request_20251029_170728_909adbab.json)
        config_path: Path to config file
    
    Returns:
        Dict with all extraction results
    """
    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Load OCR request file
    with open(ocr_file_path, 'r', encoding='utf-8') as f:
        request_data = json.load(f)
    
    # Extract OCR text from request
    ocr_text = request_data['payload']['messages'][1]['content']
    
    # Split into individual receipts
    logger.info(f"📄 Processing file: {ocr_file_path}")
    splitter = ReceiptSplitter()
    receipts = splitter.split_by_page_markers(ocr_text)
    
    logger.info(f"✂️ Split into {len(receipts)} receipts")
    
    # Extract all receipts using batch processing (recommended)
    extractor = BatchReceiptExtractor(config)
    start_time = time.time()
    results = extractor.extract_all_receipts_sync(receipts, save_request=True)
    total_time = time.time() - start_time
    
    # Build summary
    successful_results = [r for r in results if r.get('success')]
    failed_results = [r for r in results if not r.get('success')]
    
    # Calculate totals
    total_items = sum(len(r['data'].get('billing_items', [])) for r in successful_results)
    total_amount = 0.0
    for r in successful_results:
        amount_str = r['data'].get('total_amount', '0')
        # Clean and convert
        clean_amount = amount_str.replace(',', '').replace(' ', '')
        try:
            total_amount += float(clean_amount)
        except:
            pass
    
    summary = {
        'source_file': ocr_file_path,
        'processing_time': total_time,
        'total_receipts': len(receipts),
        'successful': len(successful_results),
        'failed': len(failed_results),
        'total_billing_items': total_items,
        'total_amount': f"{total_amount:,.2f}",
        'results': results
    }
    
    # Save summary
    output_dir = './output/parallel_extractions'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_file = os.path.join(output_dir, f"parallel_extraction_{timestamp}.json")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"📊 Summary saved to: {summary_file}")
    
    return summary


# CLI Interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Parallel Receipt Extraction')
    parser.add_argument('ocr_file', help='Path to OCR request JSON file')
    parser.add_argument('--config', default='config.json', help='Path to config file')

    args = parser.parse_args()

    # Load configuration
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Setup logging with rotation
    log_manager = setup_logging(config.get('logging', {}))
    logger.info("🚀 Parallel Extraction logging initialized")
    
    # Extract
    result = extract_multiple_receipts_from_file(args.ocr_file, args.config)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 PARALLEL EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"Source: {result['source_file']}")
    print(f"Total Receipts: {result['total_receipts']}")
    print(f"✅ Successful: {result['successful']}")
    print(f"❌ Failed: {result['failed']}")
    print(f"📋 Total Billing Items: {result['total_billing_items']}")
    print(f"💰 Total Amount: {result['total_amount']} THB")
    print(f"⏱️  Processing Time: {result['processing_time']:.2f}s")
    print(f"⚡ Average Time per Receipt: {result['processing_time']/result['total_receipts']:.2f}s")
    print(f"{'='*60}\n")

