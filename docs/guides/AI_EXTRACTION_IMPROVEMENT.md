# 🚀 การปรับปรุง AI Extraction เพื่อความแม่นยำและครบถ้วน

## 📋 ภาพรวม

ปรับปรุงระบบ AI extraction ให้:
- ✅ **ดึงข้อมูลครบถ้วน** - ไม่พลาดรายการใดๆ
- ✅ **แม่นยำมากขึ้น** - validate และตรวจสอบความถูกต้อง
- ✅ **มีประสิทธิภาพ** - retry อัตโนมัติเมื่อข้อมูลไม่ครบ

## 🎯 ปัญหาเดิม

1. **ดึงรายการไม่ครบ** - billing items ไม่ได้ทั้งหมด
2. **ไม่แม่นยำ** - บางครั้งข้อมูลผิด หรือ พลาด
3. **ไม่มีการตรวจสอบ** - ไม่รู้ว่าข้อมูลครบหรือไม่

## ✨ การปรับปรุง

### 1. 📝 Prompt ที่ชัดเจนและละเอียดขึ้น

**ก่อน:**
```
Extract billing items in format:
code | description | amount | discount | net_amount
```

**หลัง:**
```
YOU MUST EXTRACT **ALL** BILLING ITEMS FROM THE DOCUMENT.

CRITICAL REQUIREMENTS:
✓ Look for LINE ITEMS with codes like: 1.1, 1.1.1, 1.2, 1.4, 2, 2.1, etc.
✓ Each item has 5 fields separated by pipe |
✓ Format: code | description | amount | discount | net_amount
✓ Read the ENTIRE document - don't stop at first few items

EXTRACTION STEPS:
Step 1: Scan for ALL lines starting with numbers (1.1, 1.2, 2, etc.)
Step 2: For EACH line found, extract: code, description, amount, discount, net_amount
Step 3: Verify you found ALL items (count them!)
Step 4: Double-check amounts match the original text

IMPORTANT: Total items usually range from 5-30 items
If you find less than 5 items, YOU MISSED SOME - check again!
```

### 2. ✅ Validation & Verification

เพิ่มการตรวจสอบอัตโนมัติ:

```python
def _validate_extraction(data, ocr_results):
    """ตรวจสอบความครบถ้วนของข้อมูล"""
    
    # 1. ตรวจ basic fields
    if not data.get('hospital_name'):
        warning("Missing hospital_name")
    
    # 2. ตรวจจำนวน billing items
    item_count = len(data.get('billing_items', []))
    if item_count < 3:
        warning("Too few items - likely incomplete")
    
    # 3. Pattern Matching - หา billing codes ใน OCR
    potential_codes = find_billing_code_patterns(ocr_text)
    if len(potential_codes) > item_count:
        warning(f"Missing {len(potential_codes) - item_count} items")
    
    # 4. ตรวจแต่ละ item ว่ามีครบทุก field
    for item in billing_items:
        if not item.get('code') or not item.get('desc'):
            warning("Incomplete item")
```

**การตรวจสอบ:**
- ✅ ฟิลด์พื้นฐาน (hospital_name, HN, AN, gross_amount)
- ✅ จำนวน billing items (ต้องมีอย่างน้อย 3-5 รายการ)
- ✅ เปรียบเทียบกับ OCR ว่ามี billing code ที่พลาดหรือไม่
- ✅ ตรวจแต่ละ item ว่ามีครบทุก field

### 3. 🔄 Retry Logic ที่ฉลาดขึ้น

**กลไก:**
1. Attempt แรก: ส่ง prompt ปกติ
2. ถ้าข้อมูลไม่ครบ (< 70% confidence):
   - เก็บผลลัพธ์ที่ดีที่สุดไว้
   - Retry ด้วย enhanced prompt
   - เพิ่มคำเตือน: "Previous attempt found only X items. Extract ALL!"
3. เปรียบเทียบผลลัพธ์จากทุก attempt
4. Return ผลลัพธ์ที่ดีที่สุด (มี items มากที่สุด)

```python
best_result = None
best_item_count = 0

for attempt in range(max_retries):
    result = extract_data()
    item_count = len(result['billing_items'])
    
    # เก็บผลลัพธ์ที่ดีที่สุด
    if item_count > best_item_count:
        best_result = result
        best_item_count = item_count
    
    # Validate
    if is_complete(result):
        return result  # ครบแล้ว!
    else:
        # Retry with enhanced prompt
        enhance_prompt(f"Previous attempt found only {item_count} items")

return best_result  # Return ผลลัพธ์ที่ดีที่สุด
```

### 4. 🔍 Pattern Matching

ใช้ regex หา billing codes ใน OCR text:

```python
patterns = [
    r'\b(\d+\.\d+\.\d+(?:\(\d+\))?)\b',  # 1.1.1 or 1.1.1(18)
    r'\b(\d+\.\d+(?:\(\d+\))?)\b',        # 1.1 or 1.1(5)
    r'\b(\d+(?:\(\d+\))?)\s+[ก-๙A-Z]',   # 2 ค่า
]

# หา potential billing codes
found_codes = find_patterns_in_ocr()

# เปรียบเทียบกับที่ AI ดึงได้
if len(found_codes) > len(extracted_items):
    warning(f"Missing {len(found_codes) - len(extracted_items)} items")
```

**Patterns ที่รองรับ:**
- `1.1`, `1.2`, `1.3` - รายการหลัก
- `1.1.1`, `1.2.3` - รายการย่อย
- `1.1(18)`, `2(5)` - มีจำนวนในวงเล็บ

### 5. 📊 Enhanced Logging

เพิ่ม logging ที่ชัดเจนด้วย emoji:

```
🔍 Calling AI API for extraction (attempt 1/3)
📝 AI Response (first 500 chars): ...
✅ AI extraction returned: 12 billing items
🎯 New best result: 12 items

⚠️ Extraction INCOMPLETE:
   - Only 12 billing items - may be INCOMPLETE
   - OCR has 15 potential codes, but only 12 extracted (missing 3)

🔄 Retrying with enhanced prompt...
✅ Extraction VALIDATED and COMPLETE!
   - Hospital: โรงพยาบาลรามาธิบดี
   - HN: HN:04-24-003805
   - Billing Items: 15
   - Confidence: 95.0%
```

## 📈 ผลลัพธ์ที่คาดหวัง

### ก่อนปรับปรุง
- ดึงได้ 5-8 รายการ
- ไม่มีการตรวจสอบ
- พลาดรายการบ่อย
- ความแม่นยำ ~60-70%

### หลังปรับปรุง
- ดึงได้ 12-20 รายการ (ครบถ้วน)
- มีการ validate และตรวจสอบ
- Retry อัตโนมัติเมื่อไม่ครบ
- ความแม่นยำ ~85-95%

## 🧪 การทดสอบ

### ทดสอบด้วย API

```bash
curl -X POST "http://localhost:8888/extract/text" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": ["ใบเสร็จรับเงิน", "1.1 ค่าห้อง", "1.2 ค่ายา", ...],
    "form_id": "HL0000050"
  }'
```

### ตรวจสอบ Log

```bash
# ดู log ที่ ./logs/pipeline.log
tail -f logs/pipeline.log

# จะเห็น:
# ✅ AI extraction returned: 15 billing items
# ✅ Extraction VALIDATED and COMPLETE!
# - Confidence: 95.0%
```

### ตรวจสอบผลลัพธ์

```json
{
  "success": true,
  "data": {
    "documents": [{
      "document_info": [
        {
          "code": "billing_items",
          "value": [
            // จะมี 15-20 รายการ แทนที่จะเป็น 5-8 รายการ
          ]
        }
      ]
    }]
  }
}
```

## 💡 Tips การใช้งาน

### 1. ตรวจสอบ Log เสมอ
```bash
tail -f logs/pipeline.log | grep "billing items"
```

### 2. ดู Validation Warnings
- ถ้าเห็น "INCOMPLETE" - ข้อมูลอาจไม่ครบ
- ถ้าเห็น "Missing X items" - ลองปรับ prompt

### 3. ปรับ Configuration
```json
{
  "ai_extraction": {
    "api": {
      "max_retries": 3,  // เพิ่มถ้าต้องการ retry มากขึ้น
      "temperature": 0.1, // ลดถ้าต้องการความแม่นยำ
      "max_tokens": 4000  // เพิ่มถ้า response ยาว
    },
    "prompt_optimization": {
      "max_ocr_results": 200  // เพิ่มถ้าเอกสารยาว
    }
  }
}
```

## ⚠️ ข้อควรระวัง

1. **OCR Quality** - ถ้า OCR แย่ AI ก็ดึงไม่ครบ
2. **Document Format** - บางฟอร์มอาจมี structure แปลก
3. **API Timeout** - ถ้า prompt ยาวมาก อาจ timeout
4. **Token Limit** - ถ้าข้อมูลเยอะ อาจเกิน max_tokens

## 🚀 Next Steps

1. **ทดสอบกับเอกสารจริง** - ดูว่าดึงครบหรือไม่
2. **ปรับ Threshold** - ถ้าเข้มเกินไปก็ปรับลด
3. **เพิ่ม Custom Validation** - สำหรับ form แต่ละประเภท
4. **Monitor Performance** - ดู response time และความแม่นยำ

---

**Updated:** 19 ตุลาคม 2567  
**Version:** 2.2.0  
**Status:** ✅ พร้อมใช้งาน

