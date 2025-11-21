# 🚨 URGENT: API Server ต้อง RESTART!

## ❌ ปัญหาที่เกิด

```json
{"error": "AI simple extraction failed after all retries"}
```

**สาเหตุ:**
```log
2025-10-11 22:42:02,400 - ai_simple_extraction - WARNING - AI API returned status 400: 
{'error': 'The number of tokens to keep from the initial prompt is greater than 
the context length. Try to load the model with a larger context length, or 
provide a shorter input'}
```

**และยังเห็น:**
```log
ai_simple_extraction - INFO - OCR processing: 1 total texts, sending 1 to AI (limit: 30)
```

## ⚠️ ปัญหาหลัก

**API Server ยังไม่ได้ RESTART!**

- แก้ `config.json` แล้ว ✅
  - `max_ocr_results: 100`
  - `max_tokens: 2500`
- แต่ API Server **ยังใช้ค่าเก่า** ❌
  - ยังเห็น `(limit: 30)` แทนที่จะเป็น `(limit: 100)`

---

## ✅ วิธีแก้ (ทำทันที!)

### **Step 1: หยุด API Server**

ไปที่ terminal ที่รัน API Server แล้ว:

```bash
# กด Ctrl+C
```

**รอให้ server shutdown สมบูรณ์**

---

### **Step 2: เริ่ม API Server ใหม่**

```bash
python api_server.py
```

**รอให้ server startup สมบูรณ์**

---

### **Step 3: ตรวจสอบว่า restart สำเร็จ**

**ดู console ควรเห็น:**
```log
2025-10-11 22:xx:xx - api_server - INFO - API Server logging initialized
2025-10-11 22:xx:xx - api_server - INFO - Two-Step AI Pipeline initialized successfully
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### **Step 4: ทดสอบอีกครั้ง**

```bash
curl -X POST http://localhost:8000/extract/text \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": ["โรงพยาบาล", "HN: 123", "AN: 456"],
    "template": "receipt"
  }'
```

**ตรวจสอบ log ควรเห็น:**
```log
ai_simple_extraction - INFO - OCR processing: 3 total texts, sending 3 to AI (limit: 100)
```

**ไม่ใช่ `(limit: 30)` อีกต่อไป!** ✅

---

## 🔍 เช็คว่า Restart สำเร็จ

### **1. ดู Log:**
```bash
Get-Content ./logs/pipeline.log -Tail 5
```

**ควรเห็น:**
```log
sending X to AI (limit: 100)  ✅
```

**ไม่ใช่:**
```log
sending X to AI (limit: 30)  ❌
```

---

### **2. ทดสอบ Health Check:**
```bash
curl http://localhost:8000/health
```

**ควรได้:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## 📋 Checklist

- [ ] หยุด API Server (Ctrl+C)
- [ ] รอให้ shutdown สมบูรณ์
- [ ] รัน `python api_server.py`
- [ ] รอให้ startup สมบูรณ์
- [ ] เห็น "Uvicorn running" message
- [ ] ทดสอบ API
- [ ] เช็ค log เห็น `(limit: 100)` ✅
- [ ] ไม่เจอ error 400 อีก

---

## 🎯 ผลลัพธ์ที่คาดหวัง

**ก่อน Restart:**
```log
❌ (limit: 30)
❌ AI API returned status 400
❌ AI simple extraction failed
```

**หลัง Restart:**
```log
✅ (limit: 100)
✅ AI API returned status 200
✅ AI simple extraction successful
```

---

## ⚡ Quick Commands

```bash
# 1. หยุด (Ctrl+C ใน terminal ที่รัน API)

# 2. เริ่มใหม่
cd C:\Users\kiattichai.yo\Desktop\ExtractForm
python api_server.py

# 3. เช็ค log (terminal ใหม่)
Get-Content ./logs/pipeline.log -Wait -Tail 20

# 4. ทดสอบ
curl http://localhost:8000/health
```

---

## 💡 Why This Happens?

**Python caches config in memory:**
- เมื่อ API Server เริ่มทำงาน จะโหลด `config.json` เข้า memory
- แก้ `config.json` ไม่ได้ reload config อัตโนมัติ
- **ต้อง restart เพื่อให้โหลด config ใหม่**

**This is normal behavior!** ไม่ใช่ bug ✅

---

## 🚨 REMEMBER

> **แก้ `config.json` = ต้อง RESTART API Server!**
> 
> **ทุกครั้ง ไม่มีข้อยกเว้น!**

---

**สร้างเมื่อ:** 11 ตุลาคม 2025  
**Priority:** 🔴 URGENT  
**Action Required:** RESTART NOW!

