import requests
import json
import time
import sys
import os

# Read Input Data
try:
    with open('Json_request/HL0000050_ocr.txt', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        if isinstance(raw_data, str):
            raw_data = json.loads(raw_data)
except Exception as e:
    print(f"❌ Error reading input file: {e}")
    sys.exit(1)

# Prepare Payload
payload = {
    "ocr_texts": raw_data.get('ocr_texts', []),
    "form_id": "HL0000050"
}

print(f"🚀 Sending Request to API with {len(payload['ocr_texts'])} OCR texts...")

try:
    # Call API
    response = requests.post(
        "http://localhost:8888/extract/text",
        json=payload,
        timeout=60
    )
    
    print(f"📡 Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        
        # Save to file for inspection
        os.makedirs('output', exist_ok=True)
        with open('output/api_test_result.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            
        if result.get('success'):
            print("\n✅ API Response Success!")
            print("💾 Saved response to output/api_test_result.json")
            
            data = result.get('data', {})
            docs = data.get('documents', [])
            if docs:
                doc_info = docs[0].get('document_info', [])
                print("\n🔍 Extracted Fields Preview:")
                for field in doc_info:
                    val = field.get('value')
                    if isinstance(val, list):
                        print(f"   - {field.get('code')}: [List: {len(val)} items]")
                        # Print first item preview
                        if len(val) > 0 and isinstance(val[0], dict):
                            first_item = val[0].get('value', [])
                            details = {f.get('code'): f.get('value') for f in first_item}
                            print(f"     Example: {json.dumps(details, ensure_ascii=False)}")
                    else:
                        print(f"   - {field.get('code')}: {val}")
        else:
            print(f"\n❌ API returned success=False: {result.get('error')}")
            
    else:
        print(f"\n❌ API Error: {response.text}")

except requests.exceptions.ConnectionError:
    print("\n❌ Connection Error: API Server is not running.")
    print("👉 Please start the server first: uvicorn api_server:app --port 8888")

except Exception as e:
    print(f"\n❌ Error: {e}")

