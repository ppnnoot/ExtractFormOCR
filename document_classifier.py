"""
Document Classification Module
แยกประเภทเอกสาร: Medical Receipt, Receipt, Others
ดึงข้อมูล classification จาก Template API
"""

import json
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from template_api_manager import TemplateAPIManager

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Hybrid Document Classifier: Weight-based + AI for maximum accuracy"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_config = config.get('ai_extraction', {})
        self.api_config = self.ai_config.get('api', {})

        # API settings
        self.endpoint = self.api_config.get('endpoint')
        self.model = self.api_config.get('model')
        self.temperature = self.api_config.get('temperature', 0.1)
        self.max_tokens = self.api_config.get('max_tokens', 4000)
        self.timeout = self.api_config.get('timeout', 120)
        self.max_retries = self.api_config.get('max_retries', 3)

        # Hybrid classification settings
        self.hybrid_config = config.get('hybrid_classification', {})
        self.hybrid_enabled = self.hybrid_config.get('enabled', True)
        self.confidence_threshold = self.hybrid_config.get('confidence_threshold', 70.0)
        self.force_ai_validation = self.hybrid_config.get('force_ai_validation', False)
        self.ai_weight = self.hybrid_config.get('ai_weight', 0.3)
        self.weight_based_weight = self.hybrid_config.get('weight_based_weight', 0.7)

        # Initialize Template API Manager
        self.template_manager = TemplateAPIManager(config)

        # Cache for document types loaded from API
        self.document_types = {}
        self._load_document_types_from_api()

    def _load_document_types_from_api(self):
        """Load document types and classification data from Template API"""
        try:
            logger.info("Loading document types from Template API...")

            # Get all templates from API
            all_templates = self.template_manager.get_all_templates()

            if not all_templates:
                logger.warning("No templates found from API, using fallback classification data")
                self._load_fallback_document_types()
                return

            # Build document types from templates
            for template in all_templates:
                form_id = template.get('form_id', '')
                doc_name = template.get('document_type', '')
                doc_name_thai = template.get('document_type_thai', '')

                if form_id:
                    # Map document types based on Form ID (similar to original mapping)
                    doc_type_key = self._map_form_id_to_doc_type(form_id, doc_name)
                    doc_config = self._create_classification_config(form_id, doc_name, doc_name_thai, doc_type_key)

                    if doc_config:
                        self.document_types[doc_type_key] = doc_config

            logger.info(f"Loaded {len(self.document_types)} document types from API: {list(self.document_types.keys())}")

        except Exception as e:
            logger.error(f"Failed to load document types from API: {e}", exc_info=True)
            self._load_fallback_document_types()

    def _map_form_id_to_doc_type(self, form_id: str, doc_name: str) -> str:
        """Map Form ID to document type key"""
        mapping = {
            'HL0000050': 'B01_RECEIPT',
            'HL0000052': 'B04_INVOICE',
            'HL0000053': 'B05_HOSPITAL_DETAIL',
            'HL0000054': 'B06_ESTIMATE_GOP',
            'HL0000055': 'B07_STATEMENT'
        }

        return mapping.get(form_id, f"{form_id}_UNKNOWN")

    def _create_classification_config(self, form_id: str, doc_name: str, doc_name_thai: str, doc_type_key: str) -> Dict[str, Any]:
        """Create classification configuration for a document type"""
        try:
            # Extract ref_code from doc_type_key (e.g., 'B01' from 'B01_RECEIPT')
            ref_code = doc_type_key.split('_')[0] if '_' in doc_type_key else doc_type_key[:3]

            # Priority mapping based on original logic
            priority_mapping = {
                'HL0000050': 1,  # Receipt-Bill (highest priority)
                'HL0000054': 2,  # Estimate/GOP
                'HL0000052': 3,  # Invoice
                'HL0000053': 4,  # Detail
                'HL0000055': 5   # Statement (lowest priority)
            }

            priority = priority_mapping.get(form_id, 3)

            # Generate classification keywords and weights based on document type
            # This is a simplified version - in production, this data should come from API
            config = self._generate_classification_data(form_id, doc_name, doc_name_thai, ref_code, priority)

            return config

        except Exception as e:
            logger.error(f"Failed to create classification config for {form_id}: {e}")
            return None

    def _generate_classification_data(self, form_id: str, doc_name: str, doc_name_thai: str, ref_code: str, priority: int) -> Dict[str, Any]:
        """Generate classification keywords and weights based on document type"""

        # Default classification data based on Form ID
        if form_id == 'HL0000050':  # Receipt-Bill
            return {
                "form_id": form_id,
                "ref_code": ref_code,
                "document_code": form_id,
                "type": "Receipt-Bill",
                "thai_name": doc_name_thai or "Receipt-Bill",
                "priority": priority,
                "priority_keywords": ['ใบเสร็จรับเงิน', 'receipt number', 'payment received', 'ชำระเงินแล้ว', 'รับเงิน', 'paid in full', 'ผู้รับเงิน', 'cash receipt', 'official receipt', 'payment confirmation', 'received with thanks', 'patient pay amount', 'insurance amount'],
                "keywords": ['ใบเสร็จ', 'receipt', 'ใบบิล', 'bill', 'received', 'payment', 'ชำระเงิน', 'paid', 'total paid', 'ใบสำคัญรับเงิน', 'ยอดชำระ', 'จ่ายเงิน', 'ชำระด้วยเงินสด', 'ไว้เป็นการถูกต้องแล้ว', 'รวมทั้งสิน', 'ชำระเป็น', 'cash payment', 'received from', 'amount received', 'received by', 'cashier', 'collected by', 'receipt no', 'patient pay amount', 'insurance amount', 'previous paid amount', 'discount amount', 'printed by', 'total amount', 'payment amount'],
                "weights": {
                    'ใบเสร็จรับเงิน': 4.5,
                    'receipt number': 3.5,
                    'official receipt': 3.5,
                    'ผู้รับเงิน': 3.5,
                    'cash receipt': 3.0,
                    'patient pay amount': 3.0,
                    'insurance amount': 2.8,
                    'payment received': 2.5,
                    'payment confirmation': 2.5,
                    'received from': 2.5,
                    'received with thanks': 2.8,
                    'รับเงิน': 2.5,
                    'ใบเสร็จ': 2.5,
                    'receipt': 2.0,
                    'receipt no': 2.5,
                    'paid': 1.8,
                    'ชำระเงิน': 2.0,
                    'paid in full': 2.5,
                    'ชำระด้วยเงินสด': 2.5,
                    'ไว้เป็นการถูกต้องแล้ว': 2.0,
                    'รวมทั้งสิน': 2.0,
                    'ชำระเป็น': 1.8,
                    'cash payment': 2.0,
                    'received by': 2.0,
                    'cashier': 1.8,
                    'collected by': 1.8,
                    'previous paid amount': 2.0,
                    'discount amount': 1.8,
                    'printed by': 2.0,
                    'total amount': 1.5,
                    'payment amount': 1.8
                },
                "patterns": ['ใบเสร็จ.*เลขที่', 'receipt.*no', 'receipt.*number', 'payment.*received', 'ชำระเงิน.*แล้ว', 'ผู้รับเงิน', 'ชำระด้วยเงินสด.*ถูกต้อง', 'received.*from', 'official.*receipt', 'received.*with.*thanks', 'payment.*confirmation', 'patient.*pay.*amount', 'insurance.*amount', 'printed.*by'],
                "negative_keywords": ['ไม่ใช่ใบเสร็จรับเงิน', 'not a receipt', 'not receipt', 'estimate', 'ประเมิน', 'guarantee', 'การันตี', 'print date', 'print time', 'detailed billing statement', 'itemized billing statement'],
                "negative_exceptions": [],
                "threshold": 4.5,
                "composite_allowed": True
            }

        elif form_id == 'HL0000052':  # Invoice
            return {
                "form_id": form_id,
                "ref_code": ref_code,
                "document_code": form_id,
                "type": "Invoice",
                "thai_name": doc_name_thai or "ใบแจ้งหนี้-ใบแจ้งเรียกเก็บ-ใบแจ้งค่ารักษา",
                "priority": priority,
                "priority_keywords": ['tax invoice', 'ใบกำกับภาษี', 'invoice number', 'ใบแจ้งหนี้', 'commercial invoice', 'vat invoice', 'inpatient statement', 'statement date', 'provisional charges', 'final charges will be known', 'บิลเงินสด', 'cash bill', 'cash sale'],
                "keywords": ['invoice', 'ใบแจ้งหนี้', 'tax invoice', 'ใบกำกับภาษี', 'invoice number', 'due date', 'amount due', 'เลขที่ใบแจ้งหนี้', 'ยอดที่ต้องชำระ', 'วันครบกำหนด', 'invoice date', 'bill to', 'sold to', 'tax id', 'vat', 'payment terms', 'net amount', 'total amount due', 'balance due', 'inpatient statement', 'statement date', 'statement', 'provisional hospital charges', 'provisional charges', 'final hospital charges', 'final charges', 'upon discharge', 'third-party payor', 'share of', 'บิลเงินสด', 'cash bill', 'cash sale', 'ผู้เสียภาษี', 'taxpayer', 'จำนวนเงิน', 'amount', 'total', 'รวม', 'บาท', 'baht'],
                "weights": {
                    'tax invoice': 2.5,
                    'ใบกำกับภาษี': 2.5,
                    'vat invoice': 2.5,
                    'บิลเงินสด': 3.5,
                    'cash bill': 3.0,
                    'cash sale': 3.0,
                    'invoice': 2.0,
                    'ใบแจ้งหนี้': 2.0,
                    'invoice number': 2.0,
                    'commercial invoice': 2.0,
                    'inpatient statement': 4.0,
                    'statement date': 3.5,
                    'statement': 2.0,
                    'provisional hospital charges': 3.5,
                    'provisional charges': 3.0,
                    'final hospital charges': 3.0,
                    'final charges': 2.5,
                    'amount due': 1.5,
                    'balance due': 1.5,
                    'payment terms': 1.5,
                    'due date': 1.5,
                    'tax id': 1.5,
                    'upon discharge': 2.5,
                    'third-party payor': 2.5,
                    'share of': 1.5,
                    'ผู้เสียภาษี': 2.0,
                    'taxpayer': 1.5,
                    'จำนวนเงิน': 1.5,
                    'amount': 1.0,
                    'total': 1.0,
                    'รวม': 1.0,
                    'บาท': 0.8,
                    'baht': 0.8
                },
                "patterns": ['tax.*invoice', 'invoice.*number', 'ใบกำกับภาษี.*เลขที่', 'vat.*invoice', 'invoice.*date', 'amount.*due', 'balance.*due', 'inpatient.*statement', 'statement.*date', 'provisional.*hospital.*charges', 'final.*charges.*will.*be.*known', 'upon.*discharge', 'cash.*bill', 'cash.*sale', 'บิล.*เงินสด'],
                "negative_keywords": ['ใบเสร็จรับเงิน', 'receipt', 'payment received', 'ชำระแล้ว', 'paid', 'รับเงิน', 'ผู้รับเงิน', 'official receipt', 'cash receipt', 'printed by', 'payment confirmation', 'received with thanks'],
                "negative_exceptions": ['cash bill', 'cash sale', 'บิลเงินสด'],
                "threshold": 3.0,
                "composite_allowed": False
            }

        elif form_id == 'HL0000053':  # Hospital Detail
            return {
                "form_id": form_id,
                "ref_code": ref_code,
                "document_code": form_id,
                "type": "detail",
                "thai_name": doc_name_thai or "รายละเอียดค่าใช้จ่าย",
                "priority": priority,
                "priority_keywords": ['ใบแจ้งรายละเอียดการรักษาพยาบาล', 'รายละเอียดค่ารักษา', 'admission date', 'discharge date', 'patient name', 'HN :', 'EN :', 'ward', 'room :', 'print date', 'print time', 'detailed billing', 'itemized statement', 'medical bill', 'admission datetime', 'discharge datetime'],
                "keywords": ['โรงพยาบาล', 'ใบแจ้งรายละเอียดการรักษาพยาบาล', 'ค่ารักษาพยาบาล', 'admission', 'discharge', 'patient name', 'ward', 'room charge', 'doctor fee', 'nursing care', 'รายละเอียดค่ารักษา', 'วันที่เข้ารักษา', 'วันที่จำหน่าย', 'ชื่อผู้ป่วย', 'เตียง', 'แพทย์', 'พยาบาล', 'diagnosis', 'treatment', 'medication', 'procedure', 'HN', 'EN', 'print date', 'print time', 'รายการค่ารักษาพยาบาล', 'ปริมาณ', 'ส่วนลด', 'คาตรวจวินิจฉัย', 'เวชภัณฑ์', 'ค่าห้อง', 'ค่าเตียง', 'ค่าอาหาร', 'hospital number', 'encounter number', 'attending physician', 'consulting doctor', 'medical record', 'bed charge', 'nursing fee', 'pharmacy', 'laboratory', 'radiology', 'medical supplies', 'quantity', 'price', 'amount', 'ward room bed', 'bill number', 'all bills', 'datetime', 'tablet', 'capsule', 'medicine', 'drug', 'mg', 'medication list'],
                "weights": {
                    'ใบแจ้งรายละเอียดการรักษาพยาบาล': 5.0,
                    'รายละเอียดค่ารักษา': 4.0,
                    'detailed billing': 4.0,
                    'itemized statement': 4.0,
                    'medical bill': 3.5,
                    'admission date': 3.0,
                    'admission datetime': 3.0,
                    'discharge date': 3.0,
                    'discharge datetime': 3.0,
                    'patient name': 2.0,
                    'HN :': 2.0,
                    'EN :': 2.5,
                    'hospital number': 2.0,
                    'encounter number': 2.0,
                    'ward': 2.5,
                    'ward room bed': 2.8,
                    'room charge': 2.0,
                    'doctor fee': 2.0,
                    'attending physician': 2.0,
                    'print date': 2.5,
                    'print time': 2.0,
                    'รายการค่ารักษาพยาบาล': 2.5,
                    'bed charge': 1.8,
                    'nursing fee': 1.8,
                    'medical record': 1.5,
                    'quantity': 1.5,
                    'price': 1.5,
                    'amount': 1.3,
                    'bill number': 1.8,
                    'all bills': 1.8,
                    'tablet': 1.3,
                    'capsule': 1.3,
                    'medication': 1.5,
                    'medication list': 2.0,
                    'mg': 1.0
                },
                "patterns": ['admission.*date', 'discharge.*date', 'patient.*name', 'ward.*room', 'รายละเอียด.*รักษา', 'HN.*:.*EN.*:', 'print.*date.*print.*time', 'detailed.*billing', 'itemized.*statement', 'hospital.*number.*encounter', 'admission.*datetime', 'discharge.*datetime', 'ward.*room.*bed', 'quantity.*price.*amount'],
                "negative_keywords": ['ใบเสร็จรับเงิน', 'receipt number', 'ผู้รับเงิน', 'ชำระเงินแล้ว', 'payment received', 'paid in full', 'ชำระด้วยเงินสด', 'ไว้เป็นการถูกต้องแล้ว', 'กรมธรรม์', 'guarantee letter', 'claim form', 'รวมทั้งสิน', 'official receipt', 'cash receipt', 'received from', 'received with thanks', 'payment confirmation', 'received by cashier', 'patient pay amount', 'insurance amount', 'previous paid amount', 'printed by', 'notification no', 'notification number', 'บริษัทประกันชีวิต', 'insurance company', 'บริษัทได้พิจารณา', 'การพิจารณาจ่ายค่าสินไหม', 'แอกซ่า', 'axa', 'inpatient statement', 'statement date', 'provisional hospital charges', 'provisional charges', 'final charges will be known', 'upon discharge'],
                "negative_exceptions": ['ไม่ใช่ใบเสร็จรับเงิน', 'not a receipt', 'not receipt'],
                "threshold": 4.5,
                "composite_allowed": False
            }

        elif form_id == 'HL0000054':  # Estimate/GOP
            return {
                "form_id": form_id,
                "ref_code": ref_code,
                "document_code": form_id,
                "type": "Estimate Medical Expense report, GOP, guarantee email",
                "thai_name": doc_name_thai or "ใบประเมินค่าใช้จ่าย-ใบการันตีความคุ้มครอง-เมลแจ้งผลการพิจารณา",
                "priority": priority,
                "priority_keywords": ['การันตีความคุ้มครอง', 'guarantee letter', 'gop', 'claim form', 'หนังสือสินไหม', 'ใบสรุปค่าใช้จ่ายการรักษาพยาบาล', 'guarantee of payment', 'insurance guarantee', 'medical expense estimate', 'notification no', 'notification number', 'บริษัทประกันชีวิต', 'insurance company', 'บริษัทได้พิจารณา', 'การพิจารณาจ่ายค่าสินไหม'],
                "keywords": ['ใบสรุปค่าใช้จ่าย', 'ใบประเมินค่าใช้จ่าย', 'การันตีความคุ้มครอง', 'หนังสือสินไหม', 'claim form', 'guarantee', 'gop', 'กรมธรรม์', 'บริษัทประกัน', 'ประกันชีวิต', 'coverage', 'ความคุ้มครอง', 'วงเงินประกัน', 'policy', 'insurance', 'estimated cost', 'claim number', 'claim no', 'เลขที่สินไหม', 'ประมาณการ', 'notification no', 'notification number', 'สินไหมทดแทน', 'ค่าสินไหม', 'สรุปค่าใช้จ่าย', 'policy number', 'insured', 'insurer', 'insurance company', 'coverage amount', 'approved amount', 'guarantee limit', 'estimated amount', 'pre-authorization', 'authorization number', 'ผู้เอาประกัน', 'บริษัทได้พิจารณา', 'ให้ความคุ้มครอง', 'พิจารณาคุ้มครอง', 'การพิจารณาจ่าย', 'แอกซ่า', 'กรุงไทย', 'axa', 'krungthai'],
                "weights": {
                    'การันตีความคุ้มครอง': 4.0,
                    'guarantee letter': 3.5,
                    'guarantee of payment': 3.5,
                    'insurance guarantee': 3.5,
                    'gop': 3.0,
                    'claim form': 3.0,
                    'หนังสือสินไหม': 3.0,
                    'ใบสรุปค่าใช้จ่ายการรักษาพยาบาล': 4.5,
                    'ใบสรุปค่าใช้จ่าย': 2.8,
                    'medical expense estimate': 2.8,
                    'กรมธรรม์': 2.5,
                    'policy number': 2.5,
                    'บริษัทประกัน': 3.0,
                    'ประกันชีวิต': 3.0,
                    'insurance company': 3.5,
                    'บริษัทประกันชีวิต': 4.0,
                    'claim number': 2.5,
                    'claim no': 2.5,
                    'notification no': 3.5,
                    'notification number': 3.5,
                    'สินไหมทดแทน': 2.3,
                    'สรุปค่าใช้จ่าย': 2.0,
                    'pre-authorization': 2.3,
                    'authorization number': 2.0,
                    'approved amount': 2.0,
                    'coverage amount': 1.8,
                    'ผู้เอาประกัน': 2.5,
                    'บริษัทได้พิจารณา': 3.5,
                    'ให้ความคุ้มครอง': 2.8,
                    'พิจารณาคุ้มครอง': 2.8,
                    'การพิจารณาจ่าย': 2.8,
                    'แอกซ่า': 2.5,
                    'กรุงไทย': 2.5,
                    'axa': 2.5,
                    'krungthai': 2.5
                },
                "patterns": ['guarantee.*letter', 'claim.*form', 'claim.*no', 'claim.*number', 'notification.*no', 'notification.*number', 'policy.*number', 'การันตี.*ความคุ้มครอง', 'สรุปค่าใช้จ่าย.*รักษาพยาบาล', 'insurance.*guarantee', 'pre.*authorization', 'authorization.*number', 'บริษัท.*ประกัน.*ชีวิต', 'บริษัทได้พิจารณา.*ให้.*ความคุ้มครอง', 'การพิจารณา.*จ่าย.*ค่า.*สินไหม'],
                "negative_keywords": ['ใบเสร็จรับเงิน', 'receipt', 'payment received', 'ชำระแล้ว', 'paid', 'ผู้รับเงิน', 'official receipt', 'cash receipt', 'print date', 'print time', 'printed by'],
                "negative_exceptions": [],
                "threshold": 4.0,
                "composite_allowed": False
            }

        elif form_id == 'HL0000055':  # Statement
            return {
                "form_id": form_id,
                "ref_code": ref_code,
                "document_code": form_id,
                "type": "Statement from Hospital",
                "thai_name": doc_name_thai or "Statement รพ.",
                "priority": priority,
                "priority_keywords": ['account statement', 'billing statement', 'ใบแจ้งยอด', 'statement of account'],
                "keywords": ['statement', 'ใบแจ้งยอด', 'account statement', 'รายงานค่าใช้จ่าย', 'summary', 'สรุป', 'billing statement', 'outstanding', 'คงค้าง', 'balance', 'ยอดคงเหลือ', 'statement of account', 'account balance', 'previous balance', 'current balance', 'total outstanding', 'amount outstanding', 'statement date', 'statement period'],
                "weights": {
                    'account statement': 3.0,
                    'billing statement': 3.0,
                    'statement of account': 3.0,
                    'ใบแจ้งยอด': 2.5,
                    'statement': 2.0,
                    'outstanding': 1.5,
                    'account balance': 1.8,
                    'total outstanding': 1.8,
                    'amount outstanding': 1.8,
                    'current balance': 1.5
                },
                "patterns": ['account.*statement', 'billing.*statement', 'statement.*balance', 'statement.*of.*account', 'total.*outstanding', 'amount.*outstanding'],
                "negative_keywords": ['ใบเสร็จรับเงิน', 'receipt', 'payment received', 'รายละเอียดการรักษา', 'admission', 'discharge', 'ผู้รับเงิน', 'official receipt'],
                "negative_exceptions": [],
                "threshold": 3.5,
                "composite_allowed": False
            }

        else:
            # Unknown form ID - create minimal config
            return {
                "form_id": form_id,
                "ref_code": ref_code,
                "document_code": form_id,
                "type": doc_name or "Unknown",
                "thai_name": doc_name_thai or doc_name or "ไม่ระบุ",
                "priority": priority,
                "priority_keywords": [],
                "keywords": [doc_name.lower()] if doc_name else [],
                "weights": {},
                "patterns": [],
                "negative_keywords": [],
                "negative_exceptions": [],
                "threshold": 2.0,
                "composite_allowed": False
            }

    def _load_fallback_document_types(self):
        """Load fallback document types when API fails"""
        logger.warning("Using fallback document types (hard-coded)")

        # Minimal fallback - only basic types
        self.document_types = {
            "B01_RECEIPT": {
                "form_id": "HL0000050",
                "ref_code": "B01",
                "document_code": "HL0000050",
                "type": "Receipt-Bill",
                "thai_name": "Receipt-Bill",
                "priority": 1,
                "priority_keywords": ['ใบเสร็จรับเงิน', 'receipt number', 'payment received'],
                "keywords": ['ใบเสร็จ', 'receipt', 'ใบแจ้งหนี้', 'bill', 'payment', 'ชำระเงิน'],
                "weights": {'ใบเสร็จรับเงิน': 4.5, 'receipt number': 3.5, 'payment received': 2.5},
                "patterns": ['ใบเสร็จ.*เลขที่', 'receipt.*no'],
                "negative_keywords": ['estimate', 'ประเมิน', 'guarantee'],
                "negative_exceptions": [],
                "threshold": 4.5,
                "composite_allowed": True
            },
            "B05_HOSPITAL_DETAIL": {
                "form_id": "HL0000053",
                "ref_code": "B05",
                "document_code": "HL0000053",
                "type": "detail",
                "thai_name": "รายละเอียดค่าใช้จ่าย",
                "priority": 4,
                "priority_keywords": ['ใบแจ้งรายละเอียดการรักษาพยาบาล', 'admission date', 'discharge date'],
                "keywords": ['โรงพยาบาล', 'ค่ารักษาพยาบาล', 'admission', 'discharge', 'patient name'],
                "weights": {'ใบแจ้งรายละเอียดการรักษาพยาบาล': 5.0, 'ค่ารักษาพยาบาล': 4.0},
                "patterns": ['admission.*date', 'discharge.*date'],
                "negative_keywords": ['ใบเสร็จรับเงิน', 'receipt number'],
                "negative_exceptions": [],
                "threshold": 4.5,
                "composite_allowed": False
            }
        }

    def classify_documents(self, texts: List[str], save_request: bool = True) -> Dict[str, Any]:
        """
        Classify document types from OCR texts using hybrid approach (weight-based + AI)

        Args:
            texts: List of OCR text strings
            save_request: Save AI request/response for debugging

        Returns:
            Classification result with document types
        """
        try:
            combined_text = '\n'.join(texts[:200])  # Limit to 200 lines for performance

            # Check if hybrid mode is enabled
            logger.info(f"🔄 Hybrid enabled: {self.hybrid_enabled}, threshold: {self.confidence_threshold}, force_ai: {self.force_ai_validation}")
            if self.hybrid_enabled:
                logger.info("🔄 Starting hybrid document classification (weight-based + AI)")
                return self._classify_hybrid(texts, combined_text, save_request)
            else:
                # Use weight-based classification only
                logger.info("🔍 Starting weight-based document classification")
                classification = self._classify_with_weights(combined_text)

                if save_request:
                    request_id = self._save_weight_based_request(combined_text, classification)

                logger.info(f"✅ Weight-based classification completed: {classification.get('document_code', 'unknown')}")
                return classification

        except Exception as e:
            logger.error(f"Document classification failed: {e}", exc_info=True)
            # Return fallback classification using weight-based system
            try:
                combined_text = '\n'.join(texts[:200])
                logger.info("🔄 Using fallback weight-based classification")
                weight_result = self._classify_with_weights(combined_text)
                # Convert weight_result to string-only dict
                doc_dict = {
                    'form_id': str(weight_result.get('form_id', '')),
                    'document_code': str(weight_result.get('document_code', '')),
                    'ref_code': str(weight_result.get('ref_code', '')),
                    'document_type': str(weight_result.get('document_type', '')),
                    'thai_name': str(weight_result.get('thai_name', '')),
                    'confidence': str(weight_result.get('confidence', '0')),
                    'priority': str(weight_result.get('priority', '1')),
                    'classification_method': str(weight_result.get('classification_method', 'weight_based_fallback')),
                    'matched_keywords': str(weight_result.get('matched_keywords', '')),
                    'total_score': str(weight_result.get('total_score', '0.0')),
                    'threshold': str(weight_result.get('threshold', '0.0'))
                }

                return {
                    'success': True,
                    'documents': [doc_dict],
                    'classification': {
                        'method': 'weight_based_fallback',
                        'confidence': str(weight_result.get('confidence', '0')),
                        'ai_used': 'False'
                    }
                }
            except Exception as fallback_error:
                logger.error(f"Fallback classification also failed: {fallback_error}")
                return self._fallback_classification(texts)

    def _classify_hybrid(self, texts: List[str], combined_text: str, save_request: bool = True) -> Dict[str, Any]:
        """
        Hybrid classification: Combine weight-based and AI classification for maximum accuracy
        """
        try:
            # Step 1: Weight-based classification (fast and reliable)
            logger.info("📊 Step 1: Weight-based classification")
            weight_result = self._classify_with_weights(combined_text)

            # Convert confidence string to numeric
            weight_confidence_str = weight_result.get('confidence', '0')
            if isinstance(weight_confidence_str, str):
                if weight_confidence_str.lower() == 'high':
                    weight_confidence = 85.0
                elif weight_confidence_str.lower() == 'medium':
                    weight_confidence = 70.0
                elif weight_confidence_str.lower() == 'low':
                    weight_confidence = 50.0
                else:
                    try:
                        weight_confidence = float(weight_confidence_str)
                    except ValueError:
                        weight_confidence = 70.0  # Default to medium
            else:
                weight_confidence = float(weight_confidence_str)

            weight_form_id = weight_result.get('form_id', '')

            logger.info(f"📊 Weight-based result: {weight_form_id} (confidence: {weight_confidence}%)")

            # Step 2: Decide whether to use AI validation
            should_use_ai = (
                weight_confidence < self.confidence_threshold or
                self.force_ai_validation
            )

            if should_use_ai:
                logger.info("🤖 Step 2: AI validation required - calling AI classifier")
                ai_result = self._classify_with_ai(texts, save_request)

                if ai_result and ai_result.get('success'):
                    # Step 3: Combine results using weighted scoring
                    logger.info("⚖️ Step 3: Combining weight-based and AI results")
                    final_result = self._combine_classification_results(weight_result, ai_result)

                    # Save hybrid classification result
                    if save_request:
                        self._save_hybrid_request(combined_text, weight_result, ai_result, final_result)

                    logger.info(f"✅ Hybrid classification completed: {final_result.get('form_id', 'unknown')} (method: hybrid)")

                    # Return format expected by API (Pydantic compatible)
                    # Convert final_result to dict with string values only
                    doc_dict = {
                        'form_id': str(final_result.get('form_id', '')),
                        'document_code': str(final_result.get('document_code', '')),
                        'ref_code': str(final_result.get('ref_code', '')),
                        'document_type': str(final_result.get('document_type', '')),
                        'thai_name': str(final_result.get('thai_name', '')),
                        'confidence': str(final_result.get('confidence', '0')),
                        'priority': str(final_result.get('priority', '1')),
                        'classification_method': str(final_result.get('classification_method', 'hybrid')),
                        'matched_keywords': str(final_result.get('matched_keywords', '')),
                        'total_score': str(final_result.get('total_score', '0.0')),
                        'threshold': str(final_result.get('threshold', '0.0'))
                    }

                    return {
                        'success': True,
                        'documents': [doc_dict],
                        'classification': {
                            'method': str(final_result.get('classification_method', 'hybrid')),
                            'confidence': str(final_result.get('confidence', '0')),
                            'ai_used': 'True',
                            'agreement': str(final_result.get('ai_agreement', 'False'))
                        }
                    }
                else:
                    logger.warning("❌ AI classification failed, using weight-based result only")
                    # Save weight-based request
                    if save_request:
                        self._save_weight_based_request(combined_text, weight_result)

                    # Mark as weight-based only
                    weight_result['classification_method'] = 'weight_based_fallback'
                    # Convert weight_result to string-only dict
                    doc_dict = {
                        'form_id': str(weight_result.get('form_id', '')),
                        'document_code': str(weight_result.get('document_code', '')),
                        'ref_code': str(weight_result.get('ref_code', '')),
                        'document_type': str(weight_result.get('document_type', '')),
                        'thai_name': str(weight_result.get('thai_name', '')),
                        'confidence': str(weight_result.get('confidence', '0')),
                        'priority': str(weight_result.get('priority', '1')),
                        'classification_method': str(weight_result.get('classification_method', 'weight_based_fallback')),
                        'matched_keywords': str(weight_result.get('matched_keywords', '')),
                        'total_score': str(weight_result.get('total_score', '0.0')),
                        'threshold': str(weight_result.get('threshold', '0.0'))
                    }

                    return {
                        'success': True,
                        'documents': [doc_dict],
                        'classification': {
                            'method': 'weight_based_fallback',
                            'confidence': str(weight_result.get('confidence', '0')),
                            'ai_used': 'False'
                        }
                    }
            else:
                logger.info("✨ Step 2: Weight-based confidence sufficient, skipping AI validation")
                # Save weight-based request
                if save_request:
                    self._save_weight_based_request(combined_text, weight_result)

                weight_result['classification_method'] = 'weight_based'
                # Convert weight_result to string-only dict
                doc_dict = {
                    'form_id': str(weight_result.get('form_id', '')),
                    'document_code': str(weight_result.get('document_code', '')),
                    'ref_code': str(weight_result.get('ref_code', '')),
                    'document_type': str(weight_result.get('document_type', '')),
                    'thai_name': str(weight_result.get('thai_name', '')),
                    'confidence': str(weight_result.get('confidence', '0')),
                    'priority': str(weight_result.get('priority', '1')),
                    'classification_method': str(weight_result.get('classification_method', 'weight_based')),
                    'matched_keywords': str(weight_result.get('matched_keywords', '')),
                    'total_score': str(weight_result.get('total_score', '0.0')),
                    'threshold': str(weight_result.get('threshold', '0.0'))
                }

                return {
                    'success': True,
                    'documents': [doc_dict],
                    'classification': {
                        'method': 'weight_based',
                        'confidence': str(weight_result.get('confidence', '0')),
                        'ai_used': 'False'
                    }
                }

        except Exception as e:
            logger.error(f"Hybrid classification failed: {e}")
            # Fallback to weight-based only
            try:
                weight_result = self._classify_with_weights(combined_text)
                weight_result['classification_method'] = 'weight_based_fallback'
                if save_request:
                    self._save_weight_based_request(combined_text, weight_result)
                return weight_result
            except Exception as fallback_error:
                logger.error(f"Weight-based fallback also failed: {fallback_error}")
                return self._fallback_classification(texts)

    def _classify_with_ai(self, texts: List[str], save_request: bool = True) -> Optional[Dict[str, Any]]:
        """
        Classify document using AI (OpenAI/LM Studio API)
        """
        try:
            if not self.endpoint or not self.model:
                logger.warning("AI classification not configured - missing endpoint or model")
                return None

            # Create classification prompt
            prompt = self._create_classification_prompt(texts)
            
            # Prepare request data
            request_data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert document classifier. Analyze the provided OCR text and classify the document type based on the given categories."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            # Save request for debugging
            request_id = str(uuid.uuid4())
            if save_request:
                self._save_ai_request(request_data, request_id)
            
            # Make API call with retries
            for attempt in range(self.max_retries):
                try:
                    logger.info(f"🤖 Calling AI API for classification (attempt {attempt + 1}/{self.max_retries})")
                    
                    response = requests.post(
                        self.endpoint,
                        json=request_data,
                        headers={"Content-Type": "application/json"},
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        ai_response = response.json()
                        
                        # Save response for debugging
                        if save_request:
                            self._save_ai_response(ai_response, request_id)

                        # Parse AI response
                        return self._parse_ai_classification_response(ai_response)
                    else:
                        logger.warning(f"AI API returned status {response.status_code}: {response.text}")

                except requests.exceptions.RequestException as e:
                    logger.warning(f"AI API request failed (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    time.sleep(1)  # Wait before retry

            logger.error("AI classification failed after all retries")
            return None

        except Exception as e:
            logger.error(f"AI classification error: {e}")
            return None

    def _combine_classification_results(self, weight_result: Dict[str, Any], ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine weight-based and AI classification results using weighted scoring
        """
        try:
            # Extract confidence scores
            weight_confidence = float(weight_result.get('confidence', '0'))
            ai_confidence = float(ai_result.get('confidence', '0'))

            # Calculate weighted confidence
            combined_confidence = (
                weight_confidence * self.weight_based_weight +
                ai_confidence * self.ai_weight
            )

            # Determine final classification
            # If both agree on the same form_id, use that
            weight_form_id = weight_result.get('form_id', '')
            ai_form_id = ai_result.get('form_id', '')

            if weight_form_id == ai_form_id:
                # Both agree - use weight-based as base, enhance with AI details
                final_result = weight_result.copy()
                final_result['confidence'] = f"{combined_confidence:.1f}"
                final_result['ai_validation'] = True
                final_result['ai_agreement'] = True
                final_result['classification_method'] = 'hybrid_agreed'
                final_result['ai_result'] = {
                    'form_id': ai_form_id,
                    'confidence': f"{ai_confidence:.1f}",
                    'reasoning': ai_result.get('reasoning', '')
                }
            else:
                # They disagree - choose the one with higher weighted confidence
                weight_weighted_score = weight_confidence * self.weight_based_weight
                ai_weighted_score = ai_confidence * self.ai_weight

                if weight_weighted_score >= ai_weighted_score:
                    # Use weight-based result
                    final_result = weight_result.copy()
                    final_result['confidence'] = f"{combined_confidence:.1f}"
                    final_result['ai_validation'] = True
                    final_result['ai_agreement'] = False
                    final_result['classification_method'] = 'hybrid_weight_based_won'
                    final_result['ai_result'] = {
                        'form_id': ai_form_id,
                        'confidence': f"{ai_confidence:.1f}",
                        'reasoning': ai_result.get('reasoning', ''),
                        'disagreement_reason': 'weight_based_higher_score'
                    }
                else:
                    # Use AI result
                    final_result = ai_result.copy()
                    final_result['confidence'] = f"{combined_confidence:.1f}"
                    final_result['weight_based_validation'] = True
                    final_result['ai_agreement'] = False
                    final_result['classification_method'] = 'hybrid_ai_won'
                    final_result['weight_based_result'] = {
                        'form_id': weight_form_id,
                        'confidence': f"{weight_confidence:.1f}"
                    }

            logger.info(f"⚖️ Combined result: {final_result.get('form_id', 'unknown')} (confidence: {final_result.get('confidence', '0')}%)")
            return final_result

        except Exception as e:
            logger.error(f"Error combining classification results: {e}")
            # Return weight-based result as fallback
            weight_result['classification_method'] = 'weight_based_fallback'
            return weight_result

    def _parse_ai_classification_response(self, ai_response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse AI classification response and convert to standardized format
        Supports both JSON format and key-value text format
        """
        try:
            content = ai_response.get('choices', [{}])[0].get('message', {}).get('content', '')
            if not content:
                logger.warning("No content in AI response")
                return None

            form_id = ''
            confidence = 0
            confidence_text = 'medium'
            reasoning = ''

            # Try parsing as JSON first
            try:
                parsed = json.loads(content.strip())
                # Handle JSON format
                classification = parsed.get('classification', {})
                form_id = classification.get('form_id', '')
                confidence = classification.get('confidence', 0)
                reasoning = classification.get('reasoning', '')
                logger.info("Parsed AI response as JSON format")

            except json.JSONDecodeError:
                # Try parsing as key-value text format
                logger.info("JSON parsing failed, trying key-value text format")
                lines = content.strip().split('\n')
                parsed_data = {}

                for line in lines:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().upper()
                        value = value.strip()
                        parsed_data[key] = value

                # Extract values from parsed data
                form_id = parsed_data.get('FORM_ID', parsed_data.get('form_id', ''))
                ref_code = parsed_data.get('REF_CODE', parsed_data.get('ref_code', ''))
                confidence_text = parsed_data.get('CONFIDENCE', parsed_data.get('confidence', 'medium')).lower()
                reasoning = parsed_data.get('REASONING', parsed_data.get('reasoning', ''))

                # Convert confidence text to numeric
                if isinstance(confidence_text, str):
                    if 'high' in confidence_text:
                        confidence = 85
                    elif 'medium' in confidence_text or 'mid' in confidence_text:
                        confidence = 70
                    elif 'low' in confidence_text:
                        confidence = 50
                    else:
                        # Try to parse as number
                        try:
                            confidence = float(confidence_text)
                        except ValueError:
                            confidence = 70  # Default to medium
                else:
                    confidence = confidence_text

                logger.info(f"Parsed AI response as key-value format: {form_id}, confidence: {confidence}")

            # Map to document type
            doc_config = None
            for doc_key, config in self.document_types.items():
                if config['form_id'] == form_id:
                    doc_config = config
                    break

            if not doc_config:
                logger.warning(f"Unknown form_id from AI: {form_id}")
                return None

            # Convert to standardized format
            result = {
                'success': True,
                'form_id': form_id,
                'document_code': doc_config['document_code'],
                'ref_code': doc_config['ref_code'],
                'document_type': doc_config['type'],
                'confidence': f"{confidence:.1f}",
                'priority': str(doc_config['priority']),
                'classification_method': 'ai',
                'reasoning': reasoning,
                'matched_keywords': '',  # AI doesn't provide keyword matches
                'total_score': '0.0',  # AI doesn't use scoring
                'threshold': '0.0'  # AI doesn't use thresholds
            }

            logger.info(f"🤖 AI classification result: {form_id} (confidence: {confidence}%)")
            return result

        except Exception as e:
            logger.error(f"Error parsing AI classification response: {e}")
            return None

    def _save_hybrid_request(self, text: str, weight_result: Dict[str, Any], ai_result: Dict[str, Any], final_result: Dict[str, Any]) -> str:
        """Save hybrid classification request for debugging"""
        try:
            import uuid
            from pathlib import Path

            request_id = str(uuid.uuid4())
            debug_dir = Path("./output/ai_debug/classification")
            debug_dir.mkdir(parents=True, exist_ok=True)

            request_data = {
                "request_id": request_id,
                "timestamp": str(uuid.uuid1()),
                "method": "hybrid",
                "input_text": text[:1000],  # Limit text length
                "weight_based_result": weight_result,
                "ai_result": ai_result,
                "final_result": final_result
            }

            request_file = debug_dir / f"hybrid_classification_{request_id}.json"
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 Hybrid classification saved: {request_file}")
            return request_id

        except Exception as e:
            logger.warning(f"Failed to save hybrid classification request: {e}")
            return str(uuid.uuid4())

    def _save_ai_request(self, request_data: Dict[str, Any], request_id: str) -> None:
        """Save AI classification request for debugging"""
        try:
            from pathlib import Path
            debug_dir = Path("./output/ai_debug/classification")
            debug_dir.mkdir(parents=True, exist_ok=True)

            request_file = debug_dir / f"ai_request_{request_id}.json"
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 AI classification request saved: {request_file}")

        except Exception as e:
            logger.warning(f"Failed to save AI request: {e}")

    def _save_ai_response(self, response_data: Dict[str, Any], request_id: str) -> None:
        """Save AI classification response for debugging"""
        try:
            from pathlib import Path
            debug_dir = Path("./output/ai_debug/classification")
            debug_dir.mkdir(parents=True, exist_ok=True)

            response_file = debug_dir / f"ai_response_{request_id}.json"
            with open(response_file, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 AI classification response saved: {response_file}")

        except Exception as e:
            logger.warning(f"Failed to save AI response: {e}")

    def _classify_with_weights(self, text: str) -> Dict[str, Any]:
        """
        Classify document using weight-based system from JavaScript rules
        """
        import re

        text_lower = text.lower()
        scores = {}

        # Calculate scores for each document type
        for doc_key, doc_config in self.document_types.items():
            score = 0
            matches = []

            # Priority keywords (higher weight)
            for keyword in doc_config.get('priority_keywords', []):
                keyword_lower = keyword.lower()
                weight = doc_config['weights'].get(keyword, 1.0)  # Default weight if not specified

                # Check for keyword presence
                if keyword_lower in text_lower:
                    score += weight
                    matches.append(f"priority:{keyword}({weight})")

                # Check for patterns
                for pattern in doc_config.get('patterns', []):
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        score += weight * 0.8  # Slightly less for pattern matches
                        matches.append(f"pattern:{pattern}({weight*0.8})")

            # Regular keywords
            for keyword in doc_config.get('keywords', []):
                keyword_lower = keyword.lower()
                weight = doc_config['weights'].get(keyword, 0.5)  # Lower default weight

                if keyword_lower in text_lower:
                    score += weight
                    matches.append(f"keyword:{keyword}({weight})")

            # Check negative keywords (reduce score)
            negative_score = 0
            for neg_keyword in doc_config.get('negative_keywords', []):
                neg_keyword_lower = neg_keyword.lower()
                if neg_keyword_lower in text_lower:
                    # Check if it's an exception
                    if neg_keyword not in doc_config.get('negative_exceptions', []):
                        negative_score += 1.0
                        matches.append(f"negative:{neg_keyword}(-1.0)")

            final_score = score - negative_score
            scores[doc_key] = {
                'score': final_score,
                'matches': matches,
                'threshold': doc_config.get('threshold', 2.0),
                'priority': doc_config.get('priority', 5)
            }

        # Sort by score (descending), then by priority (ascending)
        sorted_scores = sorted(scores.items(),
                              key=lambda x: (-x[1]['score'], x[1]['priority']))

        # Find best match above threshold
        best_match = None
        for doc_key, score_info in sorted_scores:
            if score_info['score'] >= score_info['threshold']:
                best_match = (doc_key, score_info)
                break

        # If no match above threshold, use highest score anyway
        if not best_match:
            best_match = sorted_scores[0] if sorted_scores else (None, {'score': 0})

        doc_key, score_info = best_match
        doc_config = self.document_types.get(doc_key, {})

        # Create classification result (all values as strings for Pydantic)
        classification = {
            "success": True,
            "documents": [{
                "form_id": doc_config.get('form_id', ''),
                "document_code": doc_config.get('document_code', ''),
                "ref_code": doc_config.get('ref_code', ''),
                "document_type": doc_config.get('type', ''),
                "thai_name": doc_config.get('thai_name', ''),
                "confidence": ".1f",
                "priority": str(doc_config.get('priority', 5)),
                "classification_method": "weight_based",
                "matched_keywords": "; ".join(score_info['matches'][:20]),  # Convert list to string
                "total_score": ".2f",
                "threshold": ".1f"
            }],
            "processing_time": "0.0",
            "classification_details": {
                "all_scores": "; ".join([f"{k}:{v['score']:.2f}" for k, v in scores.items()]),
                "best_match": doc_key,
                "method": "weight_based_scoring"
            }
        }

        logger.info(f"📊 Classification result: {doc_key} (score: {score_info['score']:.2f}, threshold: {score_info['threshold']})")
        return classification

    def _save_weight_based_request(self, text: str, result: Dict[str, Any]) -> str:
        """Save weight-based classification request for debugging"""
        try:
            import uuid
            from pathlib import Path

            request_id = str(uuid.uuid4())
            debug_dir = Path("./output/ai_debug/classification")
            debug_dir.mkdir(parents=True, exist_ok=True)

            request_data = {
                "request_id": request_id,
                "timestamp": str(uuid.uuid1()),
                "method": "weight_based",
                "input_text": text[:1000],  # Limit text length
                "result": result
            }

            request_file = debug_dir / f"classification_{request_id}.json"
            with open(request_file, 'w', encoding='utf-8') as f:
                json.dump(request_data, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 Weight-based classification saved: {request_file}")
            return request_id
            
        except Exception as e:
            logger.warning(f"Failed to save classification request: {e}")
            return str(uuid.uuid4())
    
    def _create_classification_prompt(self, texts: List[str]) -> str:
        """Create prompt for document classification using dynamic document types from API"""

        # Combine texts (limit to reasonable length)
        combined_text = '\n'.join(texts[:100])  # Limit to 100 lines

        # Build document types section from loaded templates
        doc_types_section = "=== Document Types ===\n\n"

        form_id_list = []
        ref_code_list = []
        doc_type_list = []

        for doc_key, doc_config in self.document_types.items():
            ref_code = doc_config.get('ref_code', '')
            form_id = doc_config.get('form_id', '')
            doc_type = doc_config.get('type', '')
            thai_name = doc_config.get('thai_name', doc_type)

            # Get sample keywords
            keywords = doc_config.get('priority_keywords', [])[:5]  # Limit to 5 keywords
            keyword_str = ', '.join(keywords) if keywords else 'N/A'

            doc_types_section += f"**{ref_code} - {doc_type} ({thai_name})**\n"
            doc_types_section += f"Form ID: {form_id}\n"
            doc_types_section += f"Keywords: {keyword_str}\n"
            doc_types_section += f"ลักษณะ: {doc_config.get('description', 'เอกสารทางการแพทย์')}\n\n"

            # Collect for validation lists
            form_id_list.append(form_id)
            ref_code_list.append(ref_code)
            doc_type_list.append(doc_type)

        # Create validation strings
        form_id_options = '|'.join(form_id_list) if form_id_list else 'HL0000050|HL0000052|HL0000053|HL0000054|HL0000055'
        ref_code_options = '|'.join(ref_code_list) if ref_code_list else 'B01|B04|B05|B06|B07'
        doc_type_options = '|'.join(doc_type_list) if doc_type_list else 'Receipt-Bill|Invoice|Detail|Estimate|Statement'

        prompt = f"""Analyze the following Thai document text and classify into ONE of the available medical document types:

Document Text:
{combined_text}

{doc_types_section}=== Instructions ===
1. อ่านเอกสารและหาคำสำคัญ (keywords)
2. พิจารณาลักษณะของเอกสาร
3. เลือกประเภทที่ตรงที่สุด จากประเภทที่มีให้เลือก

Return EXACT format:
REF_CODE: <{ref_code_options}>
FORM_ID: <{form_id_options}>
DOCUMENT_TYPE: <{doc_type_options}>
CONFIDENCE: <high|medium|low>
REASONING: <why you chose this type>

Example:
REF_CODE: B05
FORM_ID: HL0000053
DOCUMENT_TYPE: Detail
CONFIDENCE: high
REASONING: พบใบแจ้งรายละเอียดค่ารักษาพยาบาล มีรายการ billing items พร้อมรหัส

IMPORTANT: Return ONLY the classification above. No explanations."""

        return prompt
    
    def _parse_classification_response(self, content: str) -> Dict[str, Any]:
        """Parse AI classification response using dynamic document types"""

        try:
            lines = content.strip().split('\n')
            ref_code = ""
            form_id = ""
            document_type = ""
            confidence = "medium"
            reasoning = "AI classification"

            for line in lines:
                if line.startswith('REF_CODE:'):
                    ref_code = line.split(':', 1)[1].strip()
                elif line.startswith('FORM_ID:'):
                    form_id = line.split(':', 1)[1].strip()
                elif line.startswith('DOCUMENT_TYPE:'):
                    document_type = line.split(':', 1)[1].strip()
                elif line.startswith('CONFIDENCE:'):
                    confidence = line.split(':', 1)[1].strip()
                elif line.startswith('REASONING:'):
                    reasoning = line.split(':', 1)[1].strip()

            # Find matching document type from loaded templates
            doc_info = None

            # Try to find by form_id first, then by ref_code
            if form_id:
                for key, info in self.document_types.items():
                    if info.get("form_id") == form_id:
                        doc_info = info
                        break

            if not doc_info and ref_code:
                for key, info in self.document_types.items():
                    if info.get("ref_code") == ref_code:
                        doc_info = info
                        break

            # Fallback to first available document type if not found
            if not doc_info and self.document_types:
                doc_info = list(self.document_types.values())[0]
                logger.warning(f"Unknown form_id/ref_code from AI ({form_id}/{ref_code}), using fallback: {doc_info.get('form_id', 'unknown')}")

            if not doc_info:
                logger.error("No document types available for fallback")
                return self._fallback_classification([])

            # Convert confidence text to numeric
            confidence_numeric = 70  # Default medium
            if confidence.lower() == 'high':
                confidence_numeric = 85
            elif confidence.lower() == 'medium':
                confidence_numeric = 70
            elif confidence.lower() == 'low':
                confidence_numeric = 50

            return {
                "success": True,
                "form_id": doc_info.get("form_id", form_id),
                "document_code": doc_info.get("document_code", form_id),
                "ref_code": doc_info.get("ref_code", ref_code),
                "document_type": doc_info.get("type", document_type),
                "confidence": f"{confidence_numeric:.1f}",
                "priority": str(doc_info.get("priority", 3)),
                "classification_method": "ai",
                "reasoning": reasoning,
                "matched_keywords": "",  # AI doesn't provide keyword matches
                "total_score": "0.0",  # AI doesn't use scoring
                "threshold": "0.0"  # AI doesn't use thresholds
            }

        except Exception as e:
            logger.error(f"Failed to parse classification response: {e}")
            return self._fallback_classification([])
    
    def _fallback_classification(self, texts: List[str]) -> Dict[str, Any]:
        """Fallback classification using keyword matching from loaded templates"""

        combined_text = ' '.join(texts).lower()

        # Score each document type
        scores = {}

        for doc_key, doc_config in self.document_types.items():
            score = 0

            # Check priority keywords
            for keyword in doc_config.get('priority_keywords', []):
                if keyword.lower() in combined_text:
                    score += 2  # Higher weight for priority keywords

            # Check regular keywords
            for keyword in doc_config.get('keywords', []):
                if keyword.lower() in combined_text:
                    score += 1

            scores[doc_key] = score

        # Get highest scoring type
        if scores:
            best_type = max(scores, key=scores.get)
            doc_info = self.document_types[best_type]
            max_score = scores[best_type]
        else:
            # Fallback to first available type
            best_type = list(self.document_types.keys())[0] if self.document_types else None
            doc_info = list(self.document_types.values())[0] if self.document_types else {}
            max_score = 0

        # Determine confidence
        if max_score >= 5:
            confidence = "high"
        elif max_score >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        # Convert to standardized format
        return {
            "success": True,
            "form_id": doc_info.get("form_id", ""),
            "document_code": doc_info.get("document_code", ""),
            "ref_code": doc_info.get("ref_code", ""),
            "document_type": doc_info.get("type", ""),
            "confidence": "70.0",  # Default medium confidence for fallback
            "priority": str(doc_info.get("priority", 3)),
            "classification_method": "keyword_fallback",
            "matched_keywords": f"scores: {scores}",
            "total_score": str(max_score),
            "threshold": "2.0"
        }
    
    def _save_classification_request(self, payload: Dict[str, Any], prompt: str) -> str:
        """Save AI classification request for debugging"""
        
        request_id = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # Create debug directory
        debug_dir = Path('./output/ai_debug/classification_requests')
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Save request
        request_file = debug_dir / f"classification_request_{request_id}.json"
        
        request_data = {
            "request_id": request_id,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "endpoint": self.endpoint,
            "model": self.model,
            "payload": payload,
            "prompt_preview": prompt[:500] + "..." if len(prompt) > 500 else prompt
        }
        
        with open(request_file, 'w', encoding='utf-8') as f:
            json.dump(request_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Classification request saved: {request_file}")
        return request_id
    
    def _save_classification_response(self, request_id: str, response: Dict[str, Any], content: str) -> None:
        """Save AI classification response for debugging"""
        
        # Create debug directory
        debug_dir = Path('./output/ai_debug/classification_responses')
        debug_dir.mkdir(parents=True, exist_ok=True)
        
        # Save response
        response_file = debug_dir / f"classification_response_{request_id}.json"
        
        response_data = {
            "request_id": request_id,
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S'),
            "status": "success",
            "full_response": response,
            "classification_content": content
        }
        
        with open(response_file, 'w', encoding='utf-8') as f:
            json.dump(response_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Classification response saved: {response_file}")
