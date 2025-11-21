# 🚀 Quick Start Guide - Medical Receipt Extraction API

## ✅ สิ่งที่ได้ทำเสร็จแล้ว

### 1. Two-Step AI Pipeline ✅
- ✅ AI Extract แบบ Simple List (เร็ว)
- ✅ Python Format เป็น JSON (แทบไม่ใช้เวลา)
- ✅ เร็วกว่า Original 10 เท่า (36s vs 6+ min)
- ✅ Extract ได้ครบกว่า (24 items vs 15 items)

### 2. AI Request/Response Debugging ✅
- ✅ บันทึกทุก request ใน `./output/ai_debug/requests/`
- ✅ บันทึกทุก response ใน `./output/ai_debug/responses/`
- ✅ ตรวจสอบได้ว่าส่งอะไรไป AI และ AI ตอบอะไร

### 3. REST API Server ✅
- ✅ รองรับ Image File upload
- ✅ รองรับ OCR Text array (ไม่ต้องมีรูป)
- ✅ Batch processing
- ✅ Statistics endpoint
- ✅ Swagger UI Documentation

---

## 📦 Installation

```bash
# Install dependencies
pip install fastapi uvicorn python-multipart

# Or from requirements.txt
pip install -r requirements.txt
```

---

## 🎯 วิธีใช้งาน 3 แบบ

### **แบบที่ 1: Command Line (ง่ายที่สุด)**

```bash
# ประมวลผลรูปภาพเดียว
python ai_simple_extraction.py receipt.png

# ทดสอบด้วย test script
python test_two_step_pipeline.py receipt.png
```

**ผลลัพธ์:**
- JSON output: `./output/json/receipt_two_step.json`
- AI request: `./output/ai_debug/requests/request_*.json`
- AI response: `./output/ai_debug/responses/response_*.json`

---

### **แบบที่ 2: REST API (แนะนำสำหรับ Production)**

#### **เริ่ม Server:**
```bash
# Start API server
python api_server.py

# Custom port
python api_server.py --port 8080

# With auto-reload (development)
python api_server.py --reload
```

**API จะเริ่มที่:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs (Swagger UI)
- Health: http://localhost:8000/health

#### **ใช้งาน API:**

**A. Extract from Image File (มีรูป)**

```bash
# cURL
curl -X POST http://localhost:8000/extract/image \
  -F "file=@receipt.png" \
  -o result.json

# Python
import requests

with open('receipt.png', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/extract/image', files=files)
    result = response.json()
    
print(f"Success: {result['success']}")
print(f"Billing Items: {len(result['data']['extracted_data']['document_info'][-1]['value'])}")
```

**B. Extract from OCR Text (ไม่ต้องมีรูป) ⭐**

```bash
# cURL
curl -X POST http://localhost:8000/extract/text \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": [
      "โรงพยาบาลกรุงเทพ จันทบุรี",
      "HN: 04-24-003805",
      "EN: E04-24-007371",
      "วันที่: 31/03/2024"
    ]
  }' \
  -o result.json

# Python
import requests

payload = {
    "ocr_texts": [
        "โรงพยาบาลกรุงเทพ จันทบุรี",
        "HN: 04-24-003805",
        "EN: E04-24-007371",
        "วันที่: 31/03/2024",
        "รวมเงิน: 32,657.00",
        "1.1 ค่ายาและสารอาหารทางหลอดเลือด",
        "5,294.00",
        "529.40",
        "4,764.60"
    ],
    "metadata": {"source": "external_ocr"}
}

response = requests.post('http://localhost:8000/extract/text', json=payload)
result = response.json()

print(f"Success: {result['success']}")
```

**C. Batch Processing**

```python
import requests

files = [
    ('files', open('receipt1.png', 'rb')),
    ('files', open('receipt2.png', 'rb')),
    ('files', open('receipt3.png', 'rb'))
]

response = requests.post('http://localhost:8000/extract/batch', files=files)
result = response.json()

print(f"Total: {result['total']}")
print(f"Success: {result['successful']}")
print(f"Failed: {result['failed']}")
```

---

### **แบบที่ 3: Python Library (สำหรับ Integration)**

```python
from ai_simple_extraction import TwoStepAIPipeline

# Initialize pipeline
pipeline = TwoStepAIPipeline('config.json')

# Process image
result = pipeline.process_document('receipt.png')

if result['success']:
    data = result['data']
    timing = result['timing']
    
    print(f"OCR Time: {timing['ocr_time']:.2f}s")
    print(f"AI Time: {timing['ai_extraction_time']:.2f}s")
    print(f"Total: {timing['total_time']:.2f}s")
    
    # Access extracted data
    doc_info = data['extracted_data']['document_info']
    hospital = next(item['value'] for item in doc_info if item['code'] == 'hospital_name')
    print(f"Hospital: {hospital}")
```

---

## 🧪 Testing

### **Test API Server**

```bash
# Start server first
python api_server.py

# In another terminal, run tests
python test_api.py receipt.png
```

**Test Results:**
```
[PASS] Health Check
[PASS] Root Endpoint
[PASS] Image Extraction
[PASS] Text Extraction
[PASS] Statistics

Total: 5 | Passed: 5 | Failed: 0
```

### **Test Two-Step Pipeline**

```bash
# Test single image
python test_two_step_pipeline.py receipt.png

# Validate JSON structure
python test_two_step_pipeline.py --validate output.json

# Compare with original
python test_two_step_pipeline.py --compare
```

---

## 📊 Performance

### Two-Step AI Pipeline

| Metric | Value |
|--------|-------|
| **Total Time** | 36-46 seconds |
| **OCR Time** | 2-3 seconds |
| **AI Extraction** | 34-43 seconds |
| **JSON Formatting** | < 0.001 seconds |
| **Billing Items** | 24 items |
| **Success Rate** | 100% |

### AI Model Comparison

| Model | Time | Items | Winner |
|-------|------|-------|--------|
| **qwen3-4b** | 36s | 24 items | ✅ BEST |
| gpt-oss-20b | 49s | 15 items | ❌ |

---

## 📁 Output Structure

```
ExtractForm/
├── output/
│   ├── json/                          # Final JSON outputs
│   │   └── receipt_two_step.json
│   ├── raw_ocr/                       # Raw OCR results
│   │   └── receipt_ocr.json
│   └── ai_debug/                      # AI Request/Response Debug
│       ├── requests/
│       │   └── request_20251003_*.json
│       └── responses/
│           └── response_20251003_*.json
└── logs/
    └── pipeline.log                   # System logs
```

---

## 🔍 Debugging AI Requests

### View AI Request Body

```bash
# List all requests
ls output/ai_debug/requests/

# View specific request
cat output/ai_debug/requests/request_20251003_114407_6bd53df6.json
```

**Request File Contents:**
```json
{
  "request_id": "20251003_114407_6bd53df6",
  "timestamp": "2025-10-03T11:44:07",
  "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
  "model": "qwen/qwen3-4b-2507",
  "payload": {
    "model": "qwen/qwen3-4b-2507",
    "messages": [...],
    "temperature": 0.1,
    "max_tokens": 8000
  },
  "prompt_preview": "Extract information..."
}
```

### View AI Response

```bash
# View response
cat output/ai_debug/responses/response_20251003_114407_6bd53df6.json
```

**Response File Contents:**
```json
{
  "request_id": "20251003_114407_6bd53df6",
  "timestamp": "2025-10-03T11:44:51",
  "status": "success",
  "full_response": {...},
  "extracted_content": "HOSPITAL_NAME: โรงพยาบาลกรุงเทพ..."
}
```

---

## ⚙️ Configuration

Edit `config.json`:

```json
{
  "ai_extraction": {
    "api": {
      "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
      "model": "qwen/qwen3-4b-2507",
      "timeout": 180,
      "max_retries": 2,
      "temperature": 0.1,
      "max_tokens": 8000
    }
  }
}
```

---

## 📖 Documentation

- `API_DOCUMENTATION.md` - Complete API reference
- `MODEL_COMPARISON.md` - AI model comparison
- `/docs` - Swagger UI (when server running)

---

## 🎯 Common Use Cases

### Use Case 1: Web Application

```python
# Flask/FastAPI integration
@app.post("/upload")
async def upload_receipt(file: UploadFile):
    # Forward to extraction API
    response = requests.post(
        'http://localhost:8000/extract/image',
        files={'file': file.file}
    )
    return response.json()
```

### Use Case 2: Batch Processing

```python
from pathlib import Path

pipeline = TwoStepAIPipeline('config.json')

# Process all images in directory
for image_path in Path('./receipts').glob('*.png'):
    result = pipeline.process_document(image_path)
    print(f"Processed: {image_path.name}")
```

### Use Case 3: External OCR Integration

```python
# You already have OCR results from another system
ocr_texts = external_ocr_system.extract_text(image)

# Send to API
response = requests.post(
    'http://localhost:8000/extract/text',
    json={'ocr_texts': ocr_texts}
)
result = response.json()
```

---

## 🆘 Troubleshooting

### API Server not starting?

```bash
# Check if port is already in use
netstat -ano | findstr :8000

# Kill process using port
taskkill /PID <process_id> /F

# Use different port
python api_server.py --port 8080
```

### AI Extraction failing?

1. Check AI debug files in `./output/ai_debug/`
2. Verify AI server is running
3. Check `config.json` settings
4. Review logs in `./logs/pipeline.log`

### Slow performance?

- Model `qwen3-4b` is faster than `gpt-oss-20b`
- Reduce `max_ocr_results` in config
- Use `/extract/text` if you already have OCR

---

## ✅ Features Checklist

- [x] Two-Step AI Pipeline (Fast!)
- [x] AI Request/Response Debugging
- [x] REST API Server
- [x] Image upload support
- [x] OCR Text input support
- [x] Batch processing
- [x] Swagger UI Documentation
- [x] Statistics endpoint
- [x] Error handling
- [x] Logging
- [x] Testing scripts
- [x] Complete documentation

---

## 🎉 Ready for Production!

ระบบพร้อมใช้งานแล้ว! เลือกวิธีที่เหมาะกับคุณ:

- 🖥️ **Command Line** - สำหรับทดสอบและ debugging
- 🌐 **REST API** - สำหรับ integration กับระบบอื่น
- 📚 **Python Library** - สำหรับ custom application

**Start using now:**
```bash
python api_server.py
```
Then visit: http://localhost:8000/docs

Good luck! 🚀

