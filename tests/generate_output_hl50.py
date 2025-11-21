import json
import sys
import os
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_simple_extraction import SimpleAIExtractor, JSONFormatter

# 1. Setup & Read Data
try:
    with open('Json_request/HL0000050_ocr.txt', 'r', encoding='utf-8') as f:
        input_json = json.load(f)
        if isinstance(input_json, str): input_json = json.loads(input_json)
except:
    pass

# Mock AI Response based on HL0000050 content
ai_extracted_data = {
    "hospital_name": "คลินิกแพทย์ศิรินนท์",
    "hn": "123456", # Mock HN
    "an": None,
    "gross_amount": "150.00",
    "admission_date": "2022-01-05", # From OCR: 5 มค 2565
    "billing_items": [
        {
            "code": "1", 
            "description": "ค่ายา",
            "amount": "150.00",
            "discount": "0.00",
            "net_amount": "150.00"
        }
    ]
}

# 2. Process
config = {"templates": {"cache_enabled": False}, "logging": {"level": "ERROR"}}
extractor = SimpleAIExtractor(config)
formatter = JSONFormatter()

# Parse
template_keys = {'top_level': ['hospital_name', 'hn', 'gross_amount', 'admission_date'], 'billing_fields': []}
parsed = extractor._parse_ai_json_response(json.dumps(ai_extracted_data), template_keys)

# Format
# Need a mock template structure to format correctly
mock_template = {
    "form_id": "HL0000050",
    "document_type": "Medical Receipt",
    "template_structure": {
        "documents": [{
            "document_info": [
                {"code": "hospital_name", "type": "string"},
                {"code": "hn", "type": "string"},
                {"code": "admission_date", "type": "date"},
                {"code": "gross_amount", "type": "decimal"},
                {"code": "order_items", "type": "array", "value": [{"value": [
                    {"code": "item_id", "type": "string"},
                    {"code": "item_desc", "type": "string"},
                    {"code": "item_amont", "type": "decimal"}
                ]}]}
            ]
        }]
    }
}

final_json = formatter.format_to_medical_receipt_json(parsed, template_config=mock_template)

# 3. Save Output
output_path = 'output/HL0000050_result.json'
os.makedirs('output', exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(final_json, f, ensure_ascii=False, indent=2)

print(f"✅ Output saved to: {output_path}")
print(json.dumps(final_json, ensure_ascii=False, indent=2))

