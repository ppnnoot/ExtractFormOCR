# 🔄 Restart API Server Guide

## ปัญหา
หลังจากแก้ไข `ai_simple_extraction.py` เพื่อดึง `document_code` และ `document_type` จาก Template API แล้ว แต่ API server ยังไม่ได้ restart → ยังใช้ code เก่าอยู่

## ✅ วิธีแก้

### **Windows:**

#### **1. หา Process ที่กำลังรัน API Server:**
```powershell
# หา Python process ที่รัน api_server.py
Get-Process python | Where-Object {$_.MainWindowTitle -like "*api_server*"} | Stop-Process -Force

# หรือหา port 8888
netstat -ano | findstr :8888
# จากนั้น kill process ด้วย PID
taskkill /F /PID <PID>
```

#### **2. Start API Server ใหม่:**
```powershell
# ใน PowerShell
cd C:\Users\kiattichai.yo\Desktop\ExtractForm
python api_server.py
```

หรือ

```bash
# ถ้าใช้ uvicorn
uvicorn api_server:app --host 0.0.0.0 --port 8888 --reload
```

---

### **Linux/Mac:**

#### **1. หา Process:**
```bash
# หา Python process
ps aux | grep api_server.py

# หรือหา port 8888
lsof -i :8888
```

#### **2. Kill Process:**
```bash
kill -9 <PID>
```

#### **3. Start ใหม่:**
```bash
cd /path/to/ExtractForm
python api_server.py
```

---

## 🧪 ทดสอบว่า Template API ทำงาน

### **1. Check API Stats:**
```bash
curl http://localhost:8888/stats
```

**ควรเห็น:**
```json
{
  "template_stats": {
    "api_calls": 1,
    "cache_hits": 0,
    "templates_loaded": 1
  }
}
```

---

### **2. ทดสอบ Extract:**
```bash
curl -X POST http://localhost:8888/extract/text \
  -H 'Content-Type: application/json' \
  -d '{
    "ocr_texts": ["รงพยาบาลกรุงเทพ ..."],
    "template": "medical_receipt"
  }'
```

**ตรวจสอบ response:**
```json
{
  "documents": [
    {
      "document_code": "HL0000050",     // ✅ From API (formId)
      "document_type": "Receipt-Bill",  // ✅ From API (docName)
      ...
    }
  ]
}
```

---

### **3. ตรวจสอบ Log:**
```bash
tail -f logs/pipeline.log
```

**ควรเห็น:**
```
INFO - Template loaded: Receipt-Bill (Form ID: HL0000050) in 0.005s
INFO - Using document_code from template API: HL0000050
INFO - Using document_type from template API: Receipt-Bill
```

**ไม่ควรเห็น:**
```
WARNING - Template API not available, using generated document_code: CM...
WARNING - Template API not available, using default document_type: Detail
```

---

## 🎯 Checklist

- [ ] Stop API server process
- [ ] Clear any cached Python files (`__pycache__`)
- [ ] Start API server ใหม่
- [ ] ตรวจสอบ log ว่า Template API Manager initialized
- [ ] ทดสอบ `/stats` endpoint
- [ ] ทดสอบ `/extract/text` endpoint
- [ ] ตรวจสอบว่า `document_code` = formId จาก API
- [ ] ตรวจสอบว่า `document_type` = docName จาก API

---

## 📊 Expected vs Actual

### **Before Restart (ผิด):**
```json
{
  "document_code": "CM1760594518594",  // ❌ Generated
  "document_type": "Detail"            // ❌ Hard-coded
}
```

**Log:**
```
WARNING - Template API not available, using generated document_code: CM...
```

---

### **After Restart (ถูก):**
```json
{
  "document_code": "HL0000050",     // ✅ From API
  "document_type": "Receipt-Bill"   // ✅ From API
}
```

**Log:**
```
INFO - Template loaded: Receipt-Bill (Form ID: HL0000050)
INFO - Using document_code from template API: HL0000050
INFO - Using document_type from template API: Receipt-Bill
```

---

## 🚀 Quick Start (Recommended)

```powershell
# 1. Kill existing process
Get-Process python | Where-Object {$_.CommandLine -like "*api_server*"} | Stop-Process -Force

# 2. Clear cache (optional)
Remove-Item -Recurse -Force __pycache__

# 3. Start server
python api_server.py
```

---

**สถานะ:** 🔄 **WAITING FOR RESTART**

*Restart API server แล้วทดสอบอีกครั้งครับ!* 🚀✨
