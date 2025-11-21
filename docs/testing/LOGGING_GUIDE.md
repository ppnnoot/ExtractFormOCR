# 📝 Logging Guide - ExtractForm Project

## ภาพรวม Logging System

ระบบบันทึก log ทั้งหมดไปที่ **`./logs/pipeline.log`** รวมถึง:
- ✅ API Server requests/responses
- ✅ Robot Framework test executions
- ✅ AI extraction processes
- ✅ Document classification
- ✅ Security events (authentication, rate limiting, blocked attacks)
- ✅ OCR processing
- ✅ Error tracking

---

## 📂 โครงสร้างไฟล์ Log

```
ExtractForm/
├── logs/
│   └── pipeline.log          # Main log file (รวมทุกอย่าง)
│
├── robot_results/
│   ├── log.html              # Robot Framework detailed log
│   ├── report.html           # Robot Framework test report
│   └── output.xml            # Robot Framework raw output
│
└── output/
    └── ai_debug/
        ├── requests/         # AI API request JSONs
        ├── responses/        # AI API response JSONs
        ├── classification_requests/
        └── classification_responses/
```

---

## 🔍 Log Format

### **Standard Log Entry:**
```
2025-10-08 19:13:50,123 - api_server - INFO - Processing image: receipt.png with template: medical_receipt
```

**Format:**
```
<timestamp> - <logger_name> - <level> - <message>
```

**Log Levels:**
- `DEBUG` - รายละเอียดทุกอย่าง (development)
- `INFO` - ข้อมูลทั่วไป, การทำงานปกติ
- `WARNING` - เตือนสิ่งที่อาจเป็นปัญหา
- `ERROR` - ข้อผิดพลาดที่เกิดขึ้น
- `CRITICAL` - ข้อผิดพลาดร้ายแรง

---

## 📊 ตัวอย่าง Log Entries

### **1. API Server Startup**
```log
2025-10-08 19:13:45,000 - api_server - INFO - API Server logging initialized - logs will be saved to ./logs/pipeline.log
2025-10-08 19:13:45,100 - api_server - INFO - Two-Step AI Pipeline initialized successfully
2025-10-08 19:13:45,200 - api_server - INFO - Document Classifier initialized
2025-10-08 19:13:45,300 - api_server - INFO - Security modules initialized
```

### **2. Robot Framework Test**
```log
2025-10-08 19:14:00,000 - api_server - INFO - POST /classify request received
2025-10-08 19:14:00,050 - document_classifier - INFO - Classifying 1 OCR texts
2025-10-08 19:14:00,100 - document_classifier - INFO - Classification request saved: ./output/ai_debug/classification_requests/...
2025-10-08 19:14:03,500 - document_classifier - INFO - AI classification successful (attempt 1/3)
2025-10-08 19:14:03,550 - document_classifier - INFO - Classified as: B05 (HL0000053) - Detail
2025-10-08 19:14:03,600 - api_server - INFO - Classification completed successfully
```

### **3. Extraction Process**
```log
2025-10-08 19:15:00,000 - api_server - INFO - POST /extract/text request received
2025-10-08 19:15:00,050 - api_server - INFO - Processing 5 OCR texts with template: medical_receipt
2025-10-08 19:15:00,100 - ai_simple_extraction - INFO - OCR processing: 5 total texts, sending 5 to AI (limit: 50)
2025-10-08 19:15:00,150 - ai_simple_extraction - INFO - AI request saved: ./output/ai_debug/requests/...
2025-10-08 19:15:00,200 - ai_simple_extraction - INFO - Calling AI API for simple extraction (attempt 1/2)
2025-10-08 19:15:05,000 - ai_simple_extraction - INFO - AI API response received (status 200)
2025-10-08 19:15:05,050 - ai_simple_extraction - INFO - Simple extraction completed successfully
2025-10-08 19:15:05,100 - ai_simple_extraction - INFO - JSON formatting completed in 0.0234s
2025-10-08 19:15:05,150 - api_server - INFO - Extraction completed successfully
```

### **4. Security Events**

#### **Blocked Prompt Injection:**
```log
2025-10-08 19:16:00,000 - api_server - INFO - POST /classify request received
2025-10-08 19:16:00,050 - security_module - WARNING - Potential prompt injection detected: "ignore previous instructions"
2025-10-08 19:16:00,100 - security_module - INFO - Security validation failed: Potential prompt injection detected
2025-10-08 19:16:00,150 - api_server - WARNING - Security validation failed for request
```

#### **Rate Limit Exceeded:**
```log
2025-10-08 19:17:00,000 - security_module - WARNING - Rate limit exceeded for client: 127.0.0.1
2025-10-08 19:17:00,050 - api_server - WARNING - Rate limit exceeded for request
```

#### **Authentication Failure:**
```log
2025-10-08 19:18:00,000 - security_module - WARNING - Invalid token provided
2025-10-08 19:18:00,050 - api_server - WARNING - Authentication failed for request
```

### **5. Errors**
```log
2025-10-08 19:19:00,000 - ai_simple_extraction - WARNING - AI API returned status 400: {'error': 'Prompt too long'}
2025-10-08 19:19:00,050 - ai_simple_extraction - INFO - Retrying in 1 seconds...
2025-10-08 19:19:01,100 - ai_simple_extraction - INFO - Calling AI API for simple extraction (attempt 2/2)
2025-10-08 19:19:05,000 - ai_simple_extraction - INFO - AI API response received (status 200)
```

---

## 🤖 Robot Framework + Logging

เมื่อรัน Robot Framework tests:
```bash
robot robot_tests/complete_ui_automation.robot
```

**Logs ที่เกิดขึ้น:**

### **1. Robot Log (`robot_results/log.html`)**
- รายละเอียดทุก step ของการทดสอบ
- Screenshots
- Keyword executions
- Test results

### **2. Pipeline Log (`logs/pipeline.log`)**
- API requests ที่ Robot เรียก
- Backend processing
- AI responses
- Security validations
- Errors/warnings

### **ตัวอย่างการทำงานร่วมกัน:**

**Robot Test:**
```robot
UI_FORM_B05: Classify Detail
    Go To Classify Endpoint
    Input JSON Data    {"texts":["ใบแจ้งรายละเอียด", "1.1", "1.2"]}
    Click Execute Button
```

**Logs ที่เกิด:**

**`robot_results/log.html`:**
```
✓ Go To Classify Endpoint (0.5s)
✓ Input JSON Data (0.2s)
✓ Click Execute Button (0.3s)
✓ Wait For Response (5.0s)
✓ Capture Response (0.5s)
```

**`logs/pipeline.log`:**
```log
2025-10-08 19:20:00,000 - api_server - INFO - POST /classify request received
2025-10-08 19:20:00,050 - document_classifier - INFO - Classifying 3 OCR texts
2025-10-08 19:20:00,100 - document_classifier - INFO - Found keywords: ['รายละเอียด', '1.1', '1.2']
2025-10-08 19:20:03,000 - document_classifier - INFO - Classified as: B05 (HL0000053) - Detail
2025-10-08 19:20:03,050 - api_server - INFO - Classification completed successfully
```

---

## 🔧 Configuration

### **config.json:**
```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "./logs/pipeline.log",
    "max_size": "10MB",
    "backup_count": 5
  }
}
```

### **api_server.py:**
```python
# Setup logging with file handler
log_dir = Path('./logs')
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('./logs/pipeline.log', encoding='utf-8')  # File output
    ]
)
```

---

## 📈 การดู Logs

### **1. แบบ Real-time (ขณะ Robot ทำงาน):**

**Windows PowerShell:**
```powershell
Get-Content ./logs/pipeline.log -Wait -Tail 50
```

**Linux/Mac:**
```bash
tail -f ./logs/pipeline.log
```

### **2. Search Logs:**

**หา errors:**
```powershell
Select-String -Path ./logs/pipeline.log -Pattern "ERROR"
```

**หา specific test:**
```powershell
Select-String -Path ./logs/pipeline.log -Pattern "B05"
```

**หา security events:**
```powershell
Select-String -Path ./logs/pipeline.log -Pattern "Security|WARNING"
```

### **3. Filter โดย timestamp:**
```powershell
Get-Content ./logs/pipeline.log | Select-String "2025-10-08 19:"
```

---

## 🧪 ตัวอย่างการใช้งาน

### **Scenario: รัน Robot Test และดู Logs**

**Terminal 1 - เปิด API Server:**
```bash
python api_server.py
```

**Terminal 2 - Monitor Logs:**
```bash
Get-Content ./logs/pipeline.log -Wait -Tail 50
```

**Terminal 3 - รัน Robot:**
```bash
robot robot_tests/complete_ui_automation.robot
```

**ผลลัพธ์:**
- Terminal 1: เห็น API requests/responses
- Terminal 2: เห็น real-time logs ทุกอย่าง
- Terminal 3: เห็น Robot test progress
- `robot_results/`: HTML reports
- `logs/pipeline.log`: Complete logs

---

## 🔍 Troubleshooting Logs

### **ปัญหา: Logs ไม่มีอะไรเขียน**

**สาเหตุ:**
- API Server ยังไม่ได้เปิด
- Permission denied ใน `./logs/` folder

**แก้ไข:**
```bash
# สร้าง logs folder
mkdir logs

# รัน API Server
python api_server.py
```

### **ปัญหา: Log file ใหญ่เกินไป**

**แก้ไข:**
```bash
# ลบ log เก่า
rm ./logs/pipeline.log

# หรือ backup
mv ./logs/pipeline.log ./logs/pipeline.log.backup
```

### **ปัญหา: Encoding issues (Thai characters)**

**แก้ไข:**
- ใช้ `encoding='utf-8'` ใน FileHandler (ทำแล้ว)
- เปิดดูด้วย text editor ที่รองรับ UTF-8

---

## 📋 Log Checklist สำหรับ Robot Tests

เมื่อรัน Robot tests ควรเห็นใน `logs/pipeline.log`:

- ✅ API Server startup messages
- ✅ Each API request (POST /classify, POST /extract/text)
- ✅ Classification results (REF_CODE, FORM_ID)
- ✅ Extraction results (hospital_name, HN, AN)
- ✅ Security validation results
- ✅ Blocked attacks (403 responses)
- ✅ Authentication events
- ✅ Rate limiting events
- ✅ Any errors/warnings
- ✅ Response times

---

## 🎯 สรุป

| ไฟล์ | จุดประสงค์ | เมื่อไร |
|------|----------|---------|
| `logs/pipeline.log` | รวม logs ทั้งหมด | API Server ทำงาน |
| `robot_results/log.html` | Robot test details | หลังรัน Robot |
| `robot_results/report.html` | Robot test summary | หลังรัน Robot |
| `output/ai_debug/` | AI requests/responses | เมื่อเรียก AI |

**ตอนนี้ Robot ทดสอบ → ทุก API call จะถูกบันทึกใน `logs/pipeline.log`** ✅

---

**อัปเดตล่าสุด:** 9 ตุลาคม 2025  
**Version:** 2.1.0

