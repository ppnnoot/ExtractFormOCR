import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptConfig:
    """
    Manages AI prompts for different form IDs.
    """
    
    _PROMPTS = {
        "default": {
            "doc_type": "medical document",
            "correction_prompt": (
                "You are a helpful assistant that corrects spelling errors in Thai {doc_type}. "
                "Return only the corrected text. "
                "CRITICAL RULES:\n"
                "1. REMOVE ALL COMMAS FROM NUMBERS (e.g. \"3,000.00\" -> \"3000.00\", \"6,716.00\" -> \"6716.00\").\n"
                "2. Fix incorrect decimal separators (e.g. \"2.146.00\" -> \"2146.00\").\n"
                "3. Fix spacing issues: Remove zero-width spaces (\\u200b), hair spaces, and excessive whitespace. Ensure correct spacing between Thai and English words.\n"
                "4. Ensure standard decimal format (e.g. 1234.56)."
            )
        },
        "forms": {
            "HL0000050": {
                "doc_type": "medical receipt (ใบเสร็จรับเงิน)",
                "extraction_prompt": (
                    "You are an expert at processing Thai {doc_type}. "
                    "Your task is to extract specific fields from the corrected text provided below. "
                    "Target Fields (in strict order):\n"
                    "1. hospital_name\n"
                    "2. hn\n"
                    "3. vn\n"
                    "4. receipt_date\n"
                    "5. receipt_no\n"
                    "6. patient_name\n"
                    "7. age\n"
                    "8. treatment_date\n"
                    "9. policyno\n"
                    "10. total_amount_in_writing\n"
                    "11. an\n"
                    "12. cashier_name\n"
                    "13. visit_date\n"
                    "14. patient_signature\n"
                    "15. cashier_signature\n\n"
                    "CRITICAL OUTPUT RULES:\n"
                    "- Return ONLY a single line of Tab-Separated Values (TSV).\n"
                    "- Format each field as \"key:value\" separated by tabs.\n"
                    "- NO headers, NO explanations, NO notes.\n"
                    "- Use empty string after colon for missing values (e.g. \"hn:\").\n"
                    "- You MUST produce exactly 15 fields.\n"
                    "- REMOVE ALL COMMAS from numbers.\n"
                    "- Date format: DD/MM/YYYY.\n\n"
                    "Example Output:\n"
                    "hospital_name:Bangkok Hospital\\thn:12-34-5678\\tvn:VN12345\\treceipt_date:01/01/2024\\treceipt_no:RC-001\\tpatient_name:John Doe\\tage:30\\ttreatment_date:01/01/2024\\tpolicyno:P123456\\ttotal_amount_in_writing:1500.00\\tan:AN98765\\tcashier_name:Jane Smith\\tvisit_date:01/01/2024\\tpatient_signature:Sig1\\tcashier_signature:Sig2"
                )
            },
            "HL0000052": {
                "doc_type": "medical invoice (ใบแจ้งหนี้)",
                "extraction_prompt": (
                    "You are an expert at processing Thai {doc_type}. "
                    "Your task is to extract specific fields from the corrected text provided below. "
                    "Target Fields (in strict order):\n"
                    "1. hospital_name\n"
                    "2. hn\n"
                    "3. an\n"
                    "4. invoice_on\n"
                    "5. invoice_date\n"
                    "6. company_name\n"
                    "7. discount\n"
                    "8. admission_date\n"
                    "9. discharge_date\n"
                    "10. total_admit_date\n"
                    "11. patient_name\n"
                    "12. age\n"
                    "13. doctor_name\n"
                    "14. doctor_department\n"
                    "15. company_code\n"
                    "16. service_code\n"
                    "17. branch_code\n"
                    "18. ref1\n"
                    "19. ref2\n"
                    "20. vn_en\n"
                    "21. total_invoice_amount\n"
                    "22. cashier_invoice_date\n"
                    "23. cashier_name\n"
                    "24. bed_room\n"
                    "25. ward\n\n"
                    "CRITICAL OUTPUT RULES:\n"
                    "- Return ONLY a single line of Tab-Separated Values (TSV).\n"
                    "- Format each field as \"key:value\" separated by tabs.\n"
                    "- NO headers, NO explanations, NO notes.\n"
                    "- Use empty string after colon for missing values (e.g. \"hn:\").\n"
                    "- You MUST produce exactly 25 fields.\n"
                    "- REMOVE ALL COMMAS from numbers.\n"
                    "- Date format: DD/MM/YYYY.\n\n"
                    "Example Output:\n"
                    "hospital_name:Bangkok Hospital\\thn:12-34-5678\\tan:AN98765\\tinvoice_on:INV-001\\tinvoice_date:01/01/2024\\tcompany_name:AIA\\tdiscount:500.00\\tadmission_date:01/01/2024\\tdischarge_date:03/01/2024\\ttotal_admit_date:2\\tpatient_name:John Doe\\tage:30\\tdoctor_name:Dr. Smith\\tdoctor_department:Surgery\\tcompany_code:CP01\\tservice_code:SC01\\tbranch_code:BR01\\tref1:R1\\tref2:R2\\tvn_en:VN12345\\ttotal_invoice_amount:15000.00\\tcashier_invoice_date:03/01/2024\\tcashier_name:Jane Doe\\tbed_room:503\\tward:ICU"
                )
            },
            "HL0000053": {
                "doc_type": "hospital detail (ใบแจ้งรายละเอียดค่ารักษา)",
                "extraction_prompt": (
                    "You are an expert at processing Thai {doc_type}. "
                    "Your task is to extract specific fields from the corrected text provided below. "
                    "Target Fields (in strict order):\n"
                    "1. hospital_name\n"
                    "2. hn\n"
                    "3. an\n"
                    "4. admission_date\n"
                    "5. patient_name\n"
                    "6. vn_en\n"
                    "7. amount_total\n"
                    "8. discount_total\n"
                    "9. net_amount_total\n\n"
                    "CRITICAL OUTPUT RULES:\n"
                    "- Return ONLY a single line of Tab-Separated Values (TSV).\n"
                    "- Format each field as \"key:value\" separated by tabs.\n"
                    "- NO headers, NO explanations, NO notes.\n"
                    "- Use empty string after colon for missing values (e.g. \"hn:\").\n"
                    "- You MUST produce exactly 9 fields.\n"
                    "- REMOVE ALL COMMAS from numbers.\n"
                    "- Date format: DD/MM/YYYY.\n\n"
                    "Example Output:\n"
                    "hospital_name:Bangkok Hospital\\thn:12-34-5678\\tan:AN98765\\tadmission_date:01/01/2024\\tpatient_name:John Doe\\tvn_en:VN12345\\tamount_total:5000.00\\tdiscount_total:500.00\\tnet_amount_total:4500.00"
                )
            },
            "HL0000054": {
                "doc_type": "medical estimate (ใบประเมินค่าใช้จ่าย)",
                "extraction_prompt": (
                    "You are an expert at processing Thai {doc_type}. "
                    "Your task is to extract specific fields from the corrected text provided below. "
                    "Target Fields (in strict order):\n"
                    "1. notification_no\n"
                    "2. claim_no\n"
                    "3. fund_name\n"
                    "4. patient_name\n"
                    "5. plan_name\n"
                    "6. policyno\n"
                    "7. certification_no\n"
                    "8. family_no\n"
                    "9. hospital_name\n"
                    "10. hospital_address\n"
                    "11. hospital_tel\n"
                    "12. hopital_fax\n"
                    "13. patient_fax\n"
                    "14. hn\n"
                    "15. an\n"
                    "16. admission_date\n"
                    "17. discharge_date\n\n"
                    "CRITICAL OUTPUT RULES:\n"
                    "- Return ONLY a single line of Tab-Separated Values (TSV).\n"
                    "- Format each field as \"key:value\" separated by tabs.\n"
                    "- NO headers, NO explanations, NO notes.\n"
                    "- Use empty string after colon for missing values (e.g. \"hn:\").\n"
                    "- You MUST produce exactly 17 fields.\n"
                    "- REMOVE ALL COMMAS from numbers.\n"
                    "- Date format: DD/MM/YYYY.\n\n"
                    "Example Output:\n"
                    "notification_no:N001\\tclaim_no:C001\\tfund_name:AXA\\tpatient_name:John Doe\\tplan_name:Gold\\tpolicyno:P123456\\tcertification_no:\\tfamily_no:\\thospital_name:Bangkok Hospital\\thospital_address:123 Rd.\\thospital_tel:02-123-4567\\thopital_fax:02-123-4568\\tpatient_fax:\\thn:12-34-5678\\tan:AN98765\\tadmission_date:01/01/2024\\tdischarge_date:03/01/2024"
                )
            },
            "HL0000055": {
                "doc_type": "medical statement (สรุปค่ารักษา)",
                "extraction_prompt": (
                    "You are an expert at processing Thai {doc_type}. "
                    "Your task is to extract specific fields from the corrected text provided below. "
                    "Target Fields (in strict order):\n"
                    "1. hospital_name\n"
                    "2. provider_address\n"
                    "3. tax_identification_number\n"
                    "4. fund_name\n"
                    "5. patient_name\n"
                    "6. policy_no\n"
                    "7. vn\n"
                    "8. hn\n"
                    "9. billing_number\n"
                    "10. billing_date\n"
                    "11. due_date\n"
                    "12. admission_date\n"
                    "13. discharge_date\n"
                    "14. visit_date\n"
                    "15. total_admitted_date\n"
                    "16. treatment_detail\n"
                    "17. invoice_no\n"
                    "18. total_invoice_amount\n"
                    "19. bank\n"
                    "20. account_number\n"
                    "21. billing_name\n"
                    "22. billing_signature\n"
                    "23. cashier_signature\n"
                    "24. settlement_date_and_time\n\n"
                    "CRITICAL OUTPUT RULES:\n"
                    "- Return ONLY a single line of Tab-Separated Values (TSV).\n"
                    "- Format each field as \"key:value\" separated by tabs.\n"
                    "- NO headers, NO explanations, NO notes.\n"
                    "- Use empty string after colon for missing values (e.g. \"hn:\").\n"
                    "- You MUST produce exactly 24 fields.\n"
                    "- REMOVE ALL COMMAS from numbers.\n"
                    "- Date format: DD/MM/YYYY.\n"
                    "- For 'treatment_detail', combine multiple items into a single string using '|' as separator.\n"
                    "- For 'invoice_no', combine multiple numbers into a single string using ',' as separator.\n\n"
                    "Example Output:\n"
                    "hospital_name:Bangkok Hospital\\tprovider_address:123 Rd.\\ttax_identification_number:1234567890123\\tfund_name:AXA\\tpatient_name:John Doe\\tpolicy_no:P123456\\tvn:VN12345\\thn:12-34-5678\\tbilling_number:B001\\tbilling_date:01/01/2024\\tdue_date:31/01/2024\\tadmission_date:01/01/2024\\tdischarge_date:03/01/2024\\tvisit_date:01/01/2024\\ttotal_admitted_date:2\\ttreatment_detail:1.CI001,16/04/2567,HN:123,Name1,1000.00|2.CI002,16/04/2567,HN:124,Name2,2000.00\\tinvoice_no:CI001,CI002,CI003\\ttotal_invoice_amount:15000.00\\tbank:KBANK\\taccount_number:123-4-56789-0\\tbilling_name:Admin\\tbilling_signature:Sig1\\tcashier_signature:Sig2\\tsettlement_date_and_time:03/01/2024 12:00:00"
                )
            }
        }
    }

    @classmethod
    def get_doc_type(cls, form_id: str) -> str:
        """Get document type description for a form ID"""
        form_config = cls._PROMPTS.get("forms", {}).get(form_id)
        if form_config:
            return form_config.get("doc_type", cls._PROMPTS["default"]["doc_type"])
        return cls._PROMPTS["default"]["doc_type"]

    @classmethod
    def get_correction_prompt(cls, form_id: str) -> str:
        """Get correction prompt for a form ID"""
        doc_type = cls.get_doc_type(form_id)
        base_prompt = cls._PROMPTS["default"]["correction_prompt"]
        return base_prompt.format(doc_type=doc_type)

    @classmethod
    def get_extraction_prompt(cls, form_id: str) -> str:
        """Get extraction prompt for a form ID (if available)"""
        form_config = cls._PROMPTS.get("forms", {}).get(form_id)
        if form_config and "extraction_prompt" in form_config:
            doc_type = cls.get_doc_type(form_id)
            return form_config["extraction_prompt"].format(doc_type=doc_type)
        return None

