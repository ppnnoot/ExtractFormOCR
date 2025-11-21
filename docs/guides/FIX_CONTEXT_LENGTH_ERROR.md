# 🔧 Fix: Context Length Error

## ❌ ปัญหาที่พบ

```log
2025-10-10 17:18:09,824 - ai_simple_extraction - WARNING - AI API returned status 400: 
{'error': 'The number of tokens to keep from the initial prompt is greater than the context length. 
Try to load the model with a larger context length, or provide a shorter input'}
```

**สาเหตุ:**
- Prompt ยาวเกินไป (OCR texts มีเยอะ)
- AI model มี context length จำกัด
- `max_tokens` + prompt length > model context window

---

## ✅ วิธีแก้ไข

### **1. ลด `max_ocr_results` ใน `config.json`**

**เดิม:**
```json
{
  "ai_extraction": {
    "prompt_optimization": {
      "max_ocr_results": 50  // ❌ เยอะเกิน
    }
  }
}
```

**ใหม่:**
```json
{
  "ai_extraction": {
    "api": {
      "max_tokens": 1500  // ลดจาก 2000
    },
    "prompt_optimization": {
      "max_ocr_results": 30  // ✅ ลดจาก 50
    }
  }
}
```

---

### **2. Restart API Server**

**สำคัญมาก!** ต้อง restart ทุกครั้งที่แก้ `config.json`:

```bash
# หยุด API Server (Ctrl+C)

# เริ่มใหม่
python api_server.py
```

---

### **3. ตรวจสอบว่าใช้ค่าใหม่**

ดูใน log ตอนเริ่ม API:
```log
2025-10-10 17:xx:xx - ai_simple_extraction - INFO - OCR processing: 100 total texts, sending 30 to AI (limit: 30)
```

**ถ้ายังเห็น `(limit: 50)` = ยังไม่ restart!**

---

## 📊 Recommended Settings

### **สำหรับ qwen/qwen3-4b-2507:**

| Setting | Value | เหตุผล |
|---------|-------|--------|
| `max_tokens` | 1500 | ลดจาก 2000 เพื่อเหลือพื้นที่ให้ prompt |
| `max_ocr_results` | 30 | ส่ง OCR texts แค่ 30 บรรทัดแรก |
| `temperature` | 0.1 | ต่ำ = consistent results |
| `timeout` | 120 | 2 นาที (พอสำหรับ AI processing) |
| `max_retries` | 2 | ลองใหม่ 2 ครั้งถ้า fail |

---

## 🧪 ทดสอบหลังแก้

### **Test 1: Simple extraction**
```bash
curl -X POST http://localhost:8000/extract/text \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": [
      "โรงพยาบาลกรุงเทพ",
      "HN: 04-20-006834",
      "AN: 104-24-004742",
      "รวมทั้งสิ้น: 445,205.00"
    ],
    "template": "receipt"
  }'
```

**ควรได้:**
```json
{
  "success": true,
  "transaction_no": "TX...",
  "documents": [...]
}
```

**ไม่ควรเห็น error 400**

---

### **Test 2: Robot Framework**
```bash
robot robot_tests/simple_api_tests.robot
```

**ควรผ่านทุก test**

---

## 🔍 Troubleshooting

### **ปัญหา 1: ยังเจอ error 400**

**สาเหตุ:**
- ยังไม่ restart API Server
- OCR texts ยาวมากๆ (แม้แค่ 30 บรรทัด)

**แก้ไข:**
1. Restart API Server
2. ลด `max_ocr_results` เป็น 20
3. ลด `max_tokens` เป็น 1000

---

### **ปัญหา 2: Extraction ไม่ครบ**

**สาเหตุ:**
- ลด `max_ocr_results` มากเกิน ทำให้ข้อมูลสำคัญหาย

**แก้ไข:**
- เพิ่ม `max_ocr_results` เป็น 40
- ใช้ template ที่เบากว่า (`receipt` แทน `medical_receipt`)

---

### **ปัญหา 3: AI model crash (Exit code: 6)**

**สาเหตุ:**
- Model ใช้ RAM เกิน

**แก้ไข:**
1. ลด `max_tokens` เป็น 1000
2. ลด `max_ocr_results` เป็น 20
3. ใช้ template เบา (`receipt`)
4. Restart AI model server

---

## 📈 Context Length Calculation

**Formula:**
```
Total tokens = Prompt tokens + max_tokens (response)
```

**ตัวอย่าง:**
```
Prompt (30 OCR lines) ≈ 500-800 tokens
System prompt ≈ 200 tokens
Template structure ≈ 300 tokens
max_tokens (response) = 1500 tokens
-------------------------------------------
Total ≈ 2500-3000 tokens
```

**Model context window:**
- qwen3-4b-2507: ~4096 tokens
- ต้องให้ Total < 4096

**ดังนั้น:**
- max_tokens = 1500 ✅
- max_ocr_results = 30 ✅
- Total ≈ 2500-3000 < 4096 ✅

---

## ⚙️ Advanced Settings

### **สำหรับเอกสารยาวๆ:**

**Option 1: ใช้ template เบา**
```json
{
  "template": "receipt"  // แทน "medical_receipt"
}
```

**Option 2: Split เอกสาร**
```python
# แทนที่จะส่ง 100 บรรทัด
# แบ่งเป็น 2 ครั้ง (50 + 50)
```

**Option 3: Summarize OCR**
```json
{
  "prompt_optimization": {
    "summarize_long_text": true  // เปิดอยู่แล้ว
  }
}
```

---

## ✅ Checklist

หลังแก้ไข ตรวจสอบ:

- [ ] แก้ `config.json` แล้ว
  - [ ] `max_tokens: 1500`
  - [ ] `max_ocr_results: 30`
- [ ] Restart API Server แล้ว
- [ ] ดู log เห็น `(limit: 30)`
- [ ] ทดสอบ API ไม่เจอ error 400
- [ ] Robot tests ผ่านทุก test
- [ ] Extraction ได้ข้อมูลครบถ้วน

---

## 🎯 สรุป

**ปัญหา:**
- ❌ Context length exceeded (error 400)
- ❌ AI model crash

**แก้ไข:**
- ✅ ลด `max_tokens` จาก 2000 → 1500
- ✅ ลด `max_ocr_results` จาก 50 → 30
- ✅ Restart API Server

**ผลลัพธ์:**
- ✅ ไม่เจอ error 400 อีก
- ✅ AI extraction ทำงานปกติ
- ✅ Robot tests ผ่านทุก test

---

**อัปเดต:** 10 ตุลาคม 2025  
**Version:** 2.1.1

