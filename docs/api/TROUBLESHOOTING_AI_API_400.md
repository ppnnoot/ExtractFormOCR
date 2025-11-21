# 🔧 แก้ไขปัญหา AI API Error 400

## ❌ ปัญหาที่พบ

```
2025-10-07 14:53:28,237 - ai_simple_extraction - WARNING - AI API returned status 400
Exception: AI simple extraction failed after all retries
```

---

## 🔍 สาเหตุที่เป็นไปได้

### **1. Prompt ยาวเกิน Token Limit** ⚠️ สาเหตุหลัก
- โมเดล `qwen/qwen3-4b-2507` มี context window จำกัด
- OCR text ที่ส่งไปยาวเกินไป
- จากไฟล์ request: OCR text มี **1,500+ บรรทัด**

### **2. Request Format ไม่ถูกต้อง**
- Payload format ไม่ตรงตามที่ API ต้องการ
- Model name ไม่ถูกต้อง

### **3. API Server ปัญหา**
- API server ไม่สามารถรับ request ได้
- Network timeout

---

## ✅ วิธีแก้ไข

### **วิธีที่ 1: ลด Token ที่ส่งไป (แนะนำ)**

#### **แก้ไข `config.json`**

เปลี่ยนจาก:
```json
{
  "ai_extraction": {
    "prompt_optimization": {
      "max_ocr_results": 300
    }
  }
}
```

เป็น:
```json
{
  "ai_extraction": {
    "prompt_optimization": {
      "max_ocr_results": 100
    }
  }
}
```

**คำอธิบาย:**
- ลดจำนวน OCR texts ที่ส่งไปจาก 300 เป็น 100
- จะช่วยลด token ที่ใช้ประมาณ 60-70%

---

### **วิธีที่ 2: ใช้ Template ที่เรียบง่ายกว่า**

#### **แก้ไข API Request**

เปลี่ยนจาก `template: "medical_receipt"` เป็น `template: "receipt"`

```python
# เดิม
result = pipeline.extract_from_text(ocr_texts, template="medical_receipt")

# แก้เป็น
result = pipeline.extract_from_text(ocr_texts, template="receipt")
```

**คำอธิบาย:**
- Template "receipt" มี prompt สั้นกว่า
- ไม่ต้องการ billing items รายละเอียด

---

### **วิธีที่ 3: แบ่ง OCR Text เป็นหลายส่วน**

#### **แก้ไข `ai_simple_extraction.py`**

เพิ่มการแบ่ง text ก่อนส่งไป AI:

```python
def _create_simple_prompt(self, ocr_results: List[Dict[str, Any]], template: str = "medical_receipt") -> str:
    """Create simple prompt that asks for plain text extraction based on template"""
    
    # Format OCR text (text only, sorted by position)
    texts = []
    for result in ocr_results:
        text = result.get('text', '').strip()
        if text and len(text) > 1:
            texts.append(text)
    
    # ⭐ เพิ่ม: จำกัดความยาวของแต่ละ text
    max_text_length = 100  # จำกัดแต่ละบรรทัดไม่เกิน 100 ตัวอักษร
    texts = [t[:max_text_length] for t in texts]
    
    ocr_text = '\n'.join(texts[:self.max_ocr_results])
    
    # ⭐ เพิ่ม: ตรวจสอบความยาวรวม
    max_total_chars = 5000  # จำกัดความยาวรวมไม่เกิน 5000 ตัวอักษร
    if len(ocr_text) > max_total_chars:
        ocr_text = ocr_text[:max_total_chars]
        logger.warning(f"OCR text truncated to {max_total_chars} characters")
    
    logger.info(f"OCR processing: {len(texts)} total texts, {len(ocr_text)} chars")
    
    # ... rest of the code
```

---

### **วิธีที่ 4: ตรวจสอบ Error Message จาก API**

#### **Code ที่แก้ไขแล้ว** ✅

ตอนนี้ระบบจะแสดง error detail จาก API แล้ว:

```python
else:
    error_detail = ""
    try:
        error_data = response.json()
        error_detail = f": {error_data}"
    except:
        error_detail = f": {response.text[:200]}"
    logger.warning(f"AI API returned status {response.status_code}{error_detail}")
```

**วิธีใช้:**
1. รัน API อีกครั้ง
2. ดู log ว่า error message บอกอะไร
3. แก้ไขตาม error message

---

### **วิธีที่ 5: ลด max_tokens**

#### **แก้ไข `config.json`**

เปลี่ยนจาก:
```json
{
  "ai_extraction": {
    "api": {
      "max_tokens": 8000
    }
  }
}
```

เป็น:
```json
{
  "ai_extraction": {
    "api": {
      "max_tokens": 4000
    }
  }
}
```

**คำอธิบาย:**
- ลด max_tokens ที่ขอ response
- บางครั้ง input + output tokens รวมกันเกิน context window

---

## 🧪 ทดสอบการแก้ไข

### **ขั้นตอนที่ 1: แก้ไข config.json**

```json
{
  "ai_extraction": {
    "api": {
      "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
      "model": "qwen/qwen3-4b-2507",
      "timeout": 180,
      "max_retries": 2,
      "temperature": 0.1,
      "max_tokens": 4000
    },
    "prompt_optimization": {
      "text_only_mode": true,
      "max_ocr_results": 100,
      "sort_by_position": true,
      "filter_low_confidence": true,
      "confidence_threshold": 0.5
    }
  }
}
```

**สิ่งที่เปลี่ยน:**
- `max_tokens`: 8000 → 4000
- `max_ocr_results`: 300 → 100

### **ขั้นตอนที่ 2: Restart API Server**

```bash
# หยุด API Server
Ctrl+C

# เริ่มใหม่
python api_server.py
```

### **ขั้นตอนที่ 3: ทดสอบ**

```bash
curl -X POST http://localhost:8000/extract/text \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": ["โรงพยาบาลกรุงเทพ", "HN: 04-20-006834"],
    "template": "receipt"
  }'
```

---

## 📊 การตรวจสอบ Token Usage

### **วิธีคำนวณ Tokens โดยประมาณ**

```python
# สูตรคร่าวๆ
tokens_approx = len(text) / 4  # สำหรับภาษาอังกฤษ
tokens_approx = len(text) / 2  # สำหรับภาษาไทย

# ตัวอย่าง
text = "โรงพยาบาลกรุงเทพ จันทบุรี HN: 04-20-006834"
chars = len(text)  # 48 ตัวอักษร
tokens = chars / 2  # ประมาณ 24 tokens
```

### **Token Limits ของโมเดล**

| Model | Context Window | Max Input | Max Output |
|-------|----------------|-----------|------------|
| qwen3-4b-2507 | 8,192 tokens | ~6,000 | ~2,000 |
| gpt-oss-20b | 4,096 tokens | ~3,000 | ~1,000 |

**คำแนะนำ:**
- Input + Output ต้องไม่เกิน Context Window
- ควรเหลือ buffer 10-20% สำหรับ system prompt

---

## 🔍 Debug Steps

### **1. ตรวจสอบ Request File**

```bash
# ดูไฟล์ request ล่าสุด
cat output/ai_debug/requests/request_20251007_145313_6966fcd4.json

# นับจำนวนตัวอักษร
cat output/ai_debug/requests/request_20251007_145313_6966fcd4.json | jq '.payload.messages[1].content' | wc -c
```

### **2. ทดสอบ API โดยตรง**

```bash
# ทดสอบด้วย curl
curl -X POST http://10.5.19.205:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen3-4b-2507",
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Say hello"}
    ],
    "max_tokens": 100
  }'
```

### **3. ตรวจสอบ Log**

```bash
# ดู log real-time
tail -f logs/pipeline.log

# ค้นหา error
grep "ERROR\|WARNING" logs/pipeline.log | tail -20
```

---

## ✅ Solution แนะนำ (Quick Fix)

### **แก้ไข config.json ทันที:**

```json
{
  "ai_extraction": {
    "api": {
      "max_tokens": 4000
    },
    "prompt_optimization": {
      "max_ocr_results": 80
    }
  }
}
```

### **Restart API Server:**

```bash
python api_server.py
```

### **ทดสอบอีกครั้ง:**

```bash
curl -X POST http://localhost:8000/extract/text \
  -H "Content-Type: application/json" \
  -d @test_text_request.json
```

---

## 📞 ถ้ายังไม่ได้

### **ตรวจสอบเพิ่มเติม:**

1. **API Server Status**
   ```bash
   curl http://10.5.19.205:8080/health
   ```

2. **Network Connection**
   ```bash
   ping 10.5.19.205
   ```

3. **Model Availability**
   ```bash
   curl http://10.5.19.205:8080/v1/models
   ```

4. **Check Logs on AI Server**
   - ดู log ที่ AI server (`10.5.19.205`)
   - ตรวจสอบว่ามี error อะไร

---

## 🎯 Prevention (ป้องกันปัญหา)

### **1. ตั้งค่า Monitoring**

```python
# เพิ่มใน ai_simple_extraction.py
def _create_simple_prompt(self, ...):
    # ...
    ocr_text = '\n'.join(texts[:self.max_ocr_results])
    
    # ⭐ เพิ่ม warning
    if len(ocr_text) > 5000:
        logger.warning(f"⚠️  OCR text is long ({len(ocr_text)} chars), may cause API 400")
    
    return prompt
```

### **2. ใช้ Validation**

```python
# เพิ่มการตรวจสอบก่อนส่ง
def extract_simple(self, ocr_results: List[Dict[str, Any]], ...):
    # ...
    prompt = self._create_simple_prompt(ocr_results, template)
    
    # ⭐ ตรวจสอบความยาว
    estimated_tokens = len(prompt) / 2  # ประมาณ
    if estimated_tokens > 6000:
        raise ValueError(f"Prompt too long: {estimated_tokens} tokens (max: 6000)")
    
    # ...
```

### **3. Auto-Truncate**

```python
# เพิ่มการตัดอัตโนมัติ
def _create_simple_prompt(self, ...):
    # ...
    ocr_text = '\n'.join(texts[:self.max_ocr_results])
    
    # ⭐ Auto-truncate
    MAX_CHARS = 5000
    if len(ocr_text) > MAX_CHARS:
        ocr_text = ocr_text[:MAX_CHARS]
        ocr_text += "\n\n[... text truncated ...]"
        logger.info(f"Auto-truncated to {MAX_CHARS} chars")
    
    return prompt
```

---

## 📋 Checklist การแก้ไข

- [ ] แก้ไข `config.json` ลด `max_ocr_results` เป็น 80-100
- [ ] แก้ไข `config.json` ลด `max_tokens` เป็น 4000
- [ ] Restart API server
- [ ] ทดสอบด้วย simple request
- [ ] ดู log ว่ามี error detail อะไร
- [ ] ถ้ายังไม่ได้ ลอง template "receipt" แทน
- [ ] ถ้ายังไม่ได้ ทดสอบ AI API โดยตรง

---

## 🎓 สรุป

**ปัญหา:** AI API คืนค่า 400 Bad Request

**สาเหตุหลัก:** Prompt/OCR text ยาวเกิน token limit

**วิธีแก้:**
1. ✅ ลด `max_ocr_results` จาก 300 → 100
2. ✅ ลด `max_tokens` จาก 8000 → 4000
3. ✅ ใช้ template ที่เรียบง่ายกว่า
4. ✅ Auto-truncate text ที่ยาวเกินไป

**ผลลัพธ์ที่คาดหวัง:**
- API จะคืนค่า 200 OK
- Extraction สำเร็จ
- ไม่มี retry

---

**Version:** 1.0  
**Created:** October 7, 2025  
**Status:** ✅ Ready to Use

