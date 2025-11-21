import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_simple_extraction import SimpleAIExtractor, JSONFormatter

# 1. Read Input Text
with open('Json_request/HL0000050_ocr.txt', 'r', encoding='utf-8') as f:
    input_json = json.load(f)
    # Handle cases where file might have BOM or slightly different format
    if isinstance(input_json, str):
        input_json = json.loads(input_json)
    ocr_text = input_json['ocr_texts'][0]

print(f"📄 Input OCR Text:\n{ocr_text[:200]}...\n") # Print first 200 chars

# 2. Mock AI Response (Simulating what AI would extract from this text)
# Based on text: "ค่ายา 150 ... รวมเงิน TOTAL 150"
ai_extracted_data = {
    "hospital_name": "คลินิกแพทย์ศิรินนท์",
    "hn": None,
    "gross_amount": "150.00",
    "billing_items": [
        {
            "code": "1", 
            "description": "ค่ายา",
            "amount": "150.00",
            "discount": "0.00",
            "net_amount": "150.00"
        },
         {
            "code": "-",
            "description": "กับฉยับ", # Simulating OCR noise
            "amount": "0.00",
            "discount": "0.00",
            "net_amount": "0.00"
        },
        {
            "code": "TOTAL",
            "description": "รวมเงิน TOTAL",
            "amount": "150.00"
        }
    ]
}

# 3. Run Logic
config = {
    "templates": {"cache_enabled": False},
    "logging": {"level": "ERROR"}
}
extractor = SimpleAIExtractor(config)

print("🔄 Processing...")
# Simulate Parser
template_keys = {'top_level': ['hospital_name'], 'billing_fields': []}
parsed = extractor._parse_ai_json_response(json.dumps(ai_extracted_data), template_keys)

print(f"\n✅ Parsed Data:")
print(f"   Services: {len(parsed['billing_items'])}")
print(f"   Medicines: {len(parsed['_order_items_data'])}")

print("\n[Items in Order Items (Medicines)]")
for item in parsed['_order_items_data']:
    print(f"   - {item['billing_desc']} (Amount: {item['amount']})")

print("\n[Items in Billing Items (Services)]")
for item in parsed['billing_items']:
    print(f"   - {item['billing_desc']} (Amount: {item['amount']})")

# 4. Validate "ค่ายา" should be Medicine
is_med = any("ค่ายา" in x['billing_desc'] for x in parsed['_order_items_data'])
if is_med:
    print("\n✅ Result: 'ค่ายา' correctly classified as Medicine")
else:
    print("\n❌ Result: 'ค่ายา' NOT classified as Medicine (Check keywords in ai_simple_extraction.py)")

