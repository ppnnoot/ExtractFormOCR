import logging
import re
import time
import httpx
import json
from typing import Dict, Any, List, Optional, Tuple, Union
from ai_prompts import PromptConfig

logger = logging.getLogger(__name__)

class AIExtractor:
    """
    Streamlined AI Extractor for Simple List format.
    Handles API connection (Async), retry logic, and prompt generation.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_config = config.get('ai_extraction', {})
        self.api_config = self.ai_config.get('api', {})

        # API settings
        self.endpoint = self.api_config.get('endpoint')
        self.model = self.api_config.get('model')
        self.auth_token = self.api_config.get('auth_token')
        self.timeout = self.api_config.get('timeout', 120)
        self.max_retries = self.api_config.get('max_retries', 3)
        
        # AI Generation settings
        self.temperature = self.api_config.get('temperature', 0.1)
        self.top_p = self.api_config.get('top_p', 0.8)
        self.max_tokens = self.api_config.get('simple_list_max_tokens', 4000)
        self.frequency_penalty = self.api_config.get('frequency_penalty', 0)
        self.presence_penalty = self.api_config.get('presence_penalty', 0)
        self.seed = self.api_config.get('seed', None)
        self.stop = self.api_config.get('stop', None)

    async def extract(self, ocr_text: str, form_id: Optional[str] = None) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
        """
        Main extraction method with 2-step process for specific forms.
        
        Args:
            ocr_text: The OCR text content to extract from.
            form_id: Optional Form ID to determine context (e.g. HL0000050).
            
        Returns:
            Tuple of (Raw content string from AI API, Token usage dictionary), or (None, None) if failed.
        """
        # Determine document type from form_id
        doc_type = "medical document"
        if form_id == "HL0000050":
            doc_type = "Receipt Bill (ใบเสร็จรับเงิน)"
        elif form_id == "HL0000052":
            doc_type = "Invoice (ใบแจ้งหนี้)"
        elif form_id == "HL0000053":
            doc_type = "Detail of invoice (ใบแจ้งรายละเอียดค่ารักษา)"
        elif form_id == "HL0000054":
            doc_type = "Estimate Medical Expense report, GOP, guarantee email (ใบประเมินค่าใช้จ่าย)"
        elif form_id == "HL0000055":
            doc_type = "Medical Billing Statement (สรุปค่ารักษา)"

        # --- STEP 1: Correction ---
        logger.info(f"Step 1: Correcting spelling for {form_id}...")
        correction_prompt = PromptConfig.get_correction_prompt(form_id or "default")
        
        payload_step1 = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': correction_prompt},
                {'role': 'user', 'content': f"Please correct spelling, formatting, and spacing (unicode) for this text:\n\n{ocr_text}"}
            ],
            'temperature': self.temperature,
            'top_p': self.top_p,
            'max_tokens': self.max_tokens,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty,
            'seed': self.seed,
            'stop': self.stop
        }
        
        corrected_text, usage1 = await self._call_ai_api(payload_step1)
        
        if not corrected_text:
            logger.error("Step 1 correction failed")
            return None, usage1

        # --- STEP 2: Extraction (if prompt available) ---
        extraction_prompt = PromptConfig.get_extraction_prompt(form_id or "default")
        if extraction_prompt:
            logger.info(f"Step 2: Extracting fields for {form_id}...")
            
            payload_step2 = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': extraction_prompt},
                    {'role': 'user', 'content': f"Extract data from this corrected text:\n\n{corrected_text}"}
                ],
                'temperature': 0.1, # Low temp for extraction precision
                'top_p': 0.8,
                'max_tokens': self.max_tokens
            }
            
            extracted_text, usage2 = await self._call_ai_api(payload_step2)
            
            # Combine token usage
            total_usage = self._combine_usage(usage1, usage2)
            return extracted_text, total_usage
            
        # For forms without specific extraction prompt, just return the corrected text
        return corrected_text, usage1

    async def _call_ai_api(self, payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[Dict[str, int]]]:
        """
        Executes the API call with retry logic (using async httpx).
        Returns (content, usage).
        """
        headers = {'Content-Type': 'application/json'}
        if self.auth_token:
            headers['Authorization'] = f"Bearer {self.auth_token}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"🔍 Calling AI API (attempt {attempt + 1}/{self.max_retries})")
                    response = await client.post(
                        self.endpoint,
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        usage = result.get('usage', {})
                        logger.info(f"📝 AI Response (first 200 chars): {content[:200]}")
                        return content, usage
                    else:
                        logger.warning(f"❌ AI API returned status {response.status_code}: {response.text}")
                        
                except httpx.TimeoutException:
                    logger.warning(f"⏱️ AI API timeout (attempt {attempt + 1})")
                except Exception as e:
                    logger.warning(f"❌ AI API error (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"⏳ Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    
        return None, None

    def _combine_usage(self, usage1: Optional[Dict[str, int]], usage2: Optional[Dict[str, int]]) -> Dict[str, int]:
        """Helper to combine token usage from multiple calls"""
        u1 = usage1 or {}
        u2 = usage2 or {}
        return {
            'prompt_tokens': u1.get('prompt_tokens', 0) + u2.get('prompt_tokens', 0),
            'completion_tokens': u1.get('completion_tokens', 0) + u2.get('completion_tokens', 0),
            'total_tokens': u1.get('total_tokens', 0) + u2.get('total_tokens', 0)
        }
