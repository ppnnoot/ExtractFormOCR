# 🧪 How to Test Logging

## ปัญหา
**"เวลา Robot ทำการทดสอบ ไม่เห็นมี log ไปที่ logs/pipeline.log เลย"**

## ✅ แก้ไขแล้ว

เพิ่ม **FileHandler** ใน `api_server.py` เพื่อให้ทุก API requests (รวมจาก Robot) บันทึกลงไฟล์

---

## 🧪 วิธีทดสอบ

### **1. เริ่ม API Server**
```bash
# Terminal 1
python api_server.py
```

**ควรเห็น:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
2025-10-09 19:xx:xx,xxx - api_server - INFO - API Server logging initialized - logs will be saved to ./logs/pipeline.log
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

### **2. รัน Test Script**
```bash
# Terminal 2
python test_logging.py
```

**ผลลัพธ์ที่คาดหวัง:**
```
🧪 Testing Logging Functionality
======================================================================

📝 Step 1: Check log file exists
✅ Log file exists: ./logs/pipeline.log

📏 Step 2: Get initial log size
📊 Log file size: 12,345 bytes (12.06 KB)

🚀 Step 3: Make API calls
   - Calling GET /health
     Response: 200
   - Calling POST /classify
     Response: 200
     Classified as: B01 (HL0000050)
   - Calling POST /classify (with injection)
     Response: 403 (should be 403)

📏 Step 4: Check log size after tests
📊 Log file size: 15,678 bytes (15.31 KB)

📊 Step 5: Compare log sizes
✅ SUCCESS! Log file grew by 3,333 bytes (3.25 KB)
   Initial size: 12,345 bytes
   Final size:   15,678 bytes
   Difference:   +3,333 bytes

📄 Step 6: Show recent log entries
   Last 10 lines of log:
   ------------------------------------------------------------------
   2025-10-09 19:xx:xx - api_server - INFO - GET /health request received
   2025-10-09 19:xx:xx - api_server - INFO - Health check successful
   2025-10-09 19:xx:xx - api_server - INFO - POST /classify request received
   2025-10-09 19:xx:xx - document_classifier - INFO - Classifying 3 OCR texts
   2025-10-09 19:xx:xx - document_classifier - INFO - Classified as: B01 (HL0000050)
   2025-10-09 19:xx:xx - api_server - INFO - POST /classify request received
   2025-10-09 19:xx:xx - security_module - WARNING - Potential prompt injection detected
   2025-10-09 19:xx:xx - api_server - WARNING - Security validation failed
   ------------------------------------------------------------------

======================================================================
🎉 LOGGING TEST PASSED!
✅ Logs are being written to ./logs/pipeline.log
✅ Robot Framework tests will also log to this file
======================================================================
```

---

### **3. รัน Robot Tests**
```bash
# Terminal 3
robot robot_tests/complete_ui_automation.robot
```

**ดู logs real-time:**
```bash
# Terminal 4 (Windows PowerShell)
Get-Content ./logs/pipeline.log -Wait -Tail 50

# หรือ (Linux/Mac)
tail -f ./logs/pipeline.log
```

**ควรเห็น logs แบบนี้:**
```log
2025-10-09 19:xx:xx - api_server - INFO - POST /classify request received
2025-10-09 19:xx:xx - document_classifier - INFO - Classifying 3 OCR texts
2025-10-09 19:xx:xx - document_classifier - INFO - Found keywords: ['ใบเสร็จรับเงิน', 'RECEIPT']
2025-10-09 19:xx:xx - document_classifier - INFO - Calling AI API for classification (attempt 1/3)
2025-10-09 19:xx:xx - document_classifier - INFO - AI classification successful
2025-10-09 19:xx:xx - document_classifier - INFO - Classified as: B01 (HL0000050) - Receipt-Bill
2025-10-09 19:xx:xx - api_server - INFO - Classification completed successfully
```

---

## 📂 ตรวจสอบ Log Files

### **1. ดูว่ามีไฟล์ log หรือไม่:**
```bash
ls ./logs/
```

**ควรเห็น:**
```
pipeline.log
```

### **2. ดูขนาดไฟล์:**
```bash
# Windows
Get-Item ./logs/pipeline.log | Select-Object Length, LastWriteTime

# Linux/Mac
ls -lh ./logs/pipeline.log
```

### **3. ดูบรรทัดล่าสุด:**
```bash
# Windows
Get-Content ./logs/pipeline.log -Tail 20

# Linux/Mac
tail -20 ./logs/pipeline.log
```

### **4. Search logs:**
```bash
# หา errors
Select-String -Path ./logs/pipeline.log -Pattern "ERROR"

# หา B05 classifications
Select-String -Path ./logs/pipeline.log -Pattern "B05"

# หา security events
Select-String -Path ./logs/pipeline.log -Pattern "Security|WARNING|403"
```

---

## 🔧 Troubleshooting

### **ปัญหา 1: Log file ไม่มี**
**สาเหตุ:**
- API Server ยังไม่เริ่มทำงาน
- Permission issues

**แก้ไข:**
```bash
# สร้าง logs folder
mkdir logs

# รัน API Server
python api_server.py
```

---

### **ปัญหา 2: Log file ไม่เพิ่มขนาด**
**สาเหตุ:**
- API Server ไม่ได้รับ requests
- Logging handler ไม่ถูก configure

**แก้ไข:**
1. ตรวจสอบว่า API Server รันอยู่:
   ```bash
   curl http://localhost:8000/health
   ```

2. ตรวจสอบ `api_server.py` มี FileHandler:
   ```python
   logging.basicConfig(
       handlers=[
           logging.StreamHandler(),
           logging.FileHandler('./logs/pipeline.log', encoding='utf-8')
       ]
   )
   ```

3. Restart API Server

---

### **ปัญหา 3: Thai characters ไม่แสดงผล**
**สาเหตุ:**
- Encoding issues

**แก้ไข:**
- ใช้ text editor ที่รองรับ UTF-8 (VS Code, Notepad++)
- FileHandler ใช้ `encoding='utf-8'` (ทำแล้ว)

---

## ✅ Checklist

เมื่อรัน Robot tests ควรเห็นใน `logs/pipeline.log`:

- [ ] API Server startup message
- [ ] Each POST /classify request
- [ ] Classification results (B01-B07)
- [ ] Each POST /extract/text request
- [ ] Extraction results
- [ ] Security validations
- [ ] Blocked attacks (403)
- [ ] Any errors/warnings
- [ ] Timestamps for all events

---

## 📊 Expected Log Volume

| Activity | Log Entries | Size |
|----------|-------------|------|
| API Startup | ~10 lines | 1 KB |
| 1 Classification | ~8 lines | 800 bytes |
| 1 Extraction | ~15 lines | 1.5 KB |
| 1 Security Block | ~5 lines | 500 bytes |
| **Complete Robot Test (21 tests)** | **~200 lines** | **~20 KB** |

---

## 🎯 สรุป

**การเปลี่ยนแปลง:**
```python
# เดิม (ไม่มี log file)
logging.basicConfig(
    level=logging.INFO,
    format='...'
)

# ใหม่ (มี log file)
logging.basicConfig(
    level=logging.INFO,
    format='...',
    handlers=[
        logging.StreamHandler(),  # Console
        logging.FileHandler('./logs/pipeline.log', encoding='utf-8')  # File ✅
    ]
)
```

**ผลลัพธ์:**
- ✅ ทุก API requests จะบันทึกใน `logs/pipeline.log`
- ✅ Robot tests จะมี logs
- ✅ สามารถ debug ได้ง่ายขึ้น
- ✅ มี audit trail สมบูรณ์

---

**อัปเดต:** 9 ตุลาคม 2025  
**Version:** 2.1.0

