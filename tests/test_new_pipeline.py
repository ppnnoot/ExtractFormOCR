import json
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_simple_extraction import SimpleAIExtractor, JSONFormatter

# Mock Configuration
config = {
    "templates": {
        "cache_enabled": False,
        "fallback_enabled": True,
        "directory": "./templates"
    },
    "ai_extraction": {
        "api": {
            "endpoint": "https://mock-api.com",
            "model": "mock-model"
        }
    },
    "logging": {
        "level": "ERROR" # Quiet logs
    }
}

def test_pipeline_flow():
    print("\n🚀 Testing New Pipeline Flow...\n")

    # 1. Setup Components
    extractor = SimpleAIExtractor(config)
    formatter = JSONFormatter()
    
    # 2. Mock Template Keys (เหมือนได้จาก TemplateAPIManager)
    template_keys = {
        'top_level': ['hospital_name', 'hn', 'gross_amount'],
        'billing_fields': ['billing_code', 'billing_desc', 'amount']
    }

    # 3. Mock AI Response (Flat List ตาม Prompt ใหม่)
    # สังเกต: มีทั้งยา (Paracetamol) และค่าบริการ (Nursing Fee) ปนกัน
    ai_response_content = json.dumps({
        "hospital_name": "Bangkok Hospital",
        "hn": "123456",
        "gross_amount": "1500.00",
        "billing_items": [
            {
                "code": "1.1.1",
                "description": "ค่าบริการพยาบาล (Nursing Fee)",
                "amount": "500.00",
                "discount": "0.00",
                "net_amount": "500.00"
            },
            {
                "code": "1.1.1(1)",
                "description": "Paracetamol 500 mg Tablet", 
                "amount": "100.00",
                "discount": "0.00",
                "net_amount": "100.00"
            },
            {
                "code": "1.2.1",
                "description": "Amoxycillin 500 mg Cap",
                "amount": "200.00",
                "discount": "0.00",
                "net_amount": "200.00"
            },
            {
                "code": "TOTAL",
                "description": "รวมเงินทั้งสิ้น",
                "amount": "800.00"
            }
        ]
    })

    print(f"📝 Mock AI Response:\n{ai_response_content}\n")

    # 4. Test Parsing Logic (Separation of items)
    print("🔄 Running Parser...")
    parsed_data = extractor._parse_ai_json_response(ai_response_content, template_keys)
    
    billing_items = parsed_data.get('billing_items', [])
    order_items = parsed_data.get('_order_items_data', [])
    
    print(f"\n✅ Extracted Results:")
    print(f"   - Billing Items (Services): {len(billing_items)}")
    print(f"   - Order Items (Meds): {len(order_items)}")
    
    # Validation
    has_service = any("Nursing" in x['billing_desc'] for x in billing_items)
    has_drug1 = any("Paracetamol" in x['billing_desc'] for x in order_items)
    has_drug2 = any("Amoxycillin" in x['billing_desc'] for x in order_items)
    
    if has_service and has_drug1 and has_drug2:
        print("   ✅ Categorization Logic: PASS (Services and Meds separated correctly)")
    else:
        print("   ❌ Categorization Logic: FAIL")
        print("Billing Items:", [x['billing_desc'] for x in billing_items])
        print("Order Items:", [x['billing_desc'] for x in order_items])
        
    # Check clean up summary
    has_summary = any("รวมเงิน" in x['billing_desc'] for x in billing_items)
    if not has_summary:
        print("   ✅ Summary Filter Logic: PASS (Total line removed)")
    else:
        print("   ❌ Summary Filter Logic: FAIL")

    # 5. Test Formatting Logic
    print("\n🔄 Running Formatter...")
    
    # Mock Template Structure
    mock_template_config = {
        "form_id": "TEST001",
        "template_structure": {
            "documents": [{
                "document_info": [
                    {
                        "code": "hospital_name",
                        "type": "string"
                    },
                    {
                        "code": "billing_items",
                        "type": "array",
                        "value": [{ # Template Row Schema
                            "value": [
                                {"code": "billing_code", "type": "string"},
                                {"code": "billing_desc", "type": "string"},
                                {"code": "amount", "type": "decimal"}
                            ]
                        }]
                    },
                    {
                        "code": "order_items",
                        "type": "array",
                        "value": [{ # Template Row Schema
                            "value": [
                                {"code": "item_id", "type": "string"},
                                {"code": "item_desc", "type": "string"},
                                {"code": "item_amont", "type": "decimal"}
                            ]
                        }]
                    }
                ]
            }]
        }
    }

    final_json = formatter.format_to_medical_receipt_json(
        parsed_data, 
        template_config=mock_template_config
    )
    
    # Check result structure
    doc = final_json['documents'][0]
    fields = {f['code']: f for f in doc['document_info']}
    
    final_billing = fields['billing_items']['value']
    final_orders = fields['order_items']['value']
    
    print(f"\n✅ Final JSON Output:")
    print(f"   - Formatted Billing Items: {len(final_billing)}")
    print(f"   - Formatted Order Items: {len(final_orders)}")
    
    # Check values in formatted output
    print("\n   [Sample Billing Item]")
    print(f"   {json.dumps(final_billing[0], indent=2, ensure_ascii=False)}")
    
    print("\n   [Sample Order Item]")
    print(f"   {json.dumps(final_orders[0], indent=2, ensure_ascii=False)}")
    
    if len(final_billing) == 1 and len(final_orders) == 2:
        print("\n🎉 OVERALL RESULT: PASS")
    else:
        print("\n💥 OVERALL RESULT: FAIL")

if __name__ == "__main__":
    test_pipeline_flow()

