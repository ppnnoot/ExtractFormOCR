# Medical Receipt Extraction API Documentation

## Overview

REST API สำหรับ extract ข้อมูลจาก Thai Medical Receipt โดยใช้ Two-Step AI Pipeline

- **Version**: 1.0.0
- **Base URL**: `http://localhost:8000`
- **Method**: Two-Step AI Extraction (AI Simple + Python Format)
- **Model**: qwen/qwen3-4b-2507

## Features

✅ **รองรับ 2 วิธีการส่งข้อมูล:**
1. **Image File** - อัปโหลดไฟล์รูปภาพ
2. **OCR Text** - ส่ง OCR text array

✅ **บันทึก AI Request/Response:**
- ทุก request จะถูกบันทึกใน `./output/ai_debug/requests/`
- ทุก response จะถูกบันทึกใน `./output/ai_debug/responses/`

✅ **Batch Processing:**
- รองรับการ upload หลายไฟล์พร้อมกัน

---

## Installation

```bash
# Install dependencies
pip install fastapi uvicorn python-multipart

# Or add to requirements.txt
pip install -r requirements.txt
```

---

## Starting the Server

### Basic
```bash
python api_server.py
```

### With Options
```bash
# Custom host and port
python api_server.py --host 0.0.0.0 --port 8080

# With auto-reload (development)
python api_server.py --reload
```

**Server will start at:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

---

## API Endpoints

### 1. Root Endpoint

**GET /**

Get API information

**Response:**
```json
{
  "name": "Medical Receipt Extraction API",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "POST /extract/image": "Extract from image file",
    "POST /extract/text": "Extract from OCR text",
    "GET /health": "Health check",
    "GET /stats": "API statistics"
  }
}
```

---

### 2. Health Check

**GET /health**

Check if API is running and pipeline is initialized

**Response:**
```json
{
  "status": "healthy",
  "pipeline": "initialized"
}
```

---

### 3. Extract from Image

**POST /extract/image**

Extract medical receipt data from image file

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: 
  - `file`: Image file (PNG, JPG, JPEG)

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/extract/image" \
  -F "file=@receipt.png"
```

**Example (Python):**
```python
import requests

with open('receipt.png', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/extract/image', files=files)
    result = response.json()
```

**Response:**
```json
{
  "success": true,
  "data": {
    "extraction_type": "Medical Receipt",
    "confidence": 0.95,
    "extracted_data": {
      "document_code": "CM0000095",
      "document_type": "Medical Receipt",
      "document_info": [
        {
          "code": "hospital_name",
          "value": "โรงพยาบาลกรุงเทพ จันทบุรี"
        },
        {
          "code": "hn",
          "value": "04-24-003805"
        },
        {
          "code": "billing_items",
          "value": [...]
        }
      ]
    }
  },
  "timing": {
    "ocr_time": 2.28,
    "ai_extraction_time": 34.14,
    "json_formatting_time": 0.0001,
    "total_time": 36.42
  },
  "request_id": "uuid-here"
}
```

---

### 4. Extract from OCR Text

**POST /extract/text**

Extract medical receipt data from OCR text array

**Request:**
- **Content-Type**: `application/json`
- **Body**:
```json
{
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
  "metadata": {
    "source": "external_ocr",
    "ocr_engine": "custom"
  }
}
```

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/extract/text" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": ["โรงพยาบาลกรุงเทพ", "HN: 04-24-003805"],
    "metadata": {"source": "test"}
  }'
```

**Example (Python):**
```python
import requests

payload = {
    "ocr_texts": [
        "โรงพยาบาลกรุงเทพ จันทบุรี",
        "HN: 04-24-003805",
        "EN: E04-24-007371"
    ],
    "metadata": {"source": "test"}
}

response = requests.post(
    'http://localhost:8000/extract/text',
    json=payload
)
result = response.json()
```

**Response:**
```json
{
  "success": true,
  "data": {
    "extraction_type": "Medical Receipt",
    "extracted_data": {...}
  },
  "timing": {
    "ai_extraction_time": 0
  },
  "request_id": "uuid-here"
}
```

---

### 5. Batch Extract from Images

**POST /extract/batch**

Extract from multiple images at once

**Request:**
- **Content-Type**: `multipart/form-data`
- **Body**: 
  - `files`: Multiple image files

**Example (cURL):**
```bash
curl -X POST "http://localhost:8000/extract/batch" \
  -F "files=@receipt1.png" \
  -F "files=@receipt2.png" \
  -F "files=@receipt3.png"
```

**Example (Python):**
```python
import requests

files = [
    ('files', open('receipt1.png', 'rb')),
    ('files', open('receipt2.png', 'rb')),
    ('files', open('receipt3.png', 'rb'))
]

response = requests.post(
    'http://localhost:8000/extract/batch',
    files=files
)
result = response.json()
```

**Response:**
```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "results": [
    {
      "filename": "receipt1.png",
      "success": true,
      "data": {...}
    },
    {
      "filename": "receipt2.png",
      "success": true,
      "data": {...}
    },
    {
      "filename": "receipt3.png",
      "success": false,
      "error": "OCR recognition failed"
    }
  ]
}
```

---

### 6. Get Statistics

**GET /stats**

Get API and pipeline statistics

**Response:**
```json
{
  "pipeline_stats": {
    "total_documents": 10,
    "successful_extractions": 9,
    "failed_extractions": 1,
    "success_rate": 0.9,
    "avg_processing_time": 36.42,
    "avg_ocr_time": 2.28,
    "avg_ai_time": 34.14
  },
  "api_info": {
    "version": "1.0.0",
    "model": "qwen/qwen3-4b-2507",
    "method": "Two-Step AI Extraction"
  }
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "File must be an image"
}
```

### 404 Not Found
```json
{
  "error": "Endpoint not found",
  "path": "/invalid/path"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "detail": "Error message here"
}
```

### 503 Service Unavailable
```json
{
  "detail": "Pipeline not initialized"
}
```

---

## Data Models

### ExtractionResponse

```typescript
{
  success: boolean;
  data?: {
    extraction_type: string;
    confidence: number;
    extracted_data: {
      document_code: string;
      document_type: string;
      document_info: Array<DocumentField>;
    };
    metadata: {
      source_length: number;
      processing_time: number;
      detected_language: string;
    };
  };
  error?: string;
  timing?: {
    ocr_time: number;
    ai_extraction_time: number;
    json_formatting_time: number;
    total_time: number;
  };
  request_id?: string;
}
```

### DocumentField

```typescript
{
  accuracyRate: number;
  type: string;  // "string" | "decimal" | "date" | "array"
  code: string;  // field identifier
  value: any;    // extracted value
  page: string;
}
```

---

## AI Request/Response Debugging

### Request Files

Location: `./output/ai_debug/requests/request_{timestamp}_{id}.json`

```json
{
  "request_id": "20250103_103015_abc12345",
  "timestamp": "2025-01-03T10:30:15.123456",
  "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
  "model": "qwen/qwen3-4b-2507",
  "payload": {
    "model": "qwen/qwen3-4b-2507",
    "messages": [...],
    "temperature": 0.1,
    "max_tokens": 8000
  },
  "prompt_preview": "Extract information from this Thai medical receipt..."
}
```

### Response Files

Location: `./output/ai_debug/responses/response_{timestamp}_{id}.json`

```json
{
  "request_id": "20250103_103015_abc12345",
  "timestamp": "2025-01-03T10:30:50.789012",
  "status": "success",
  "full_response": {
    "choices": [...]
  },
  "extracted_content": "HOSPITAL_NAME: โรงพยาบาลกรุงเทพ..."
}
```

---

## Testing

### Run Test Suite

```bash
# Test with default image
python test_api.py

# Test with specific image
python test_api.py path/to/receipt.png
```

### Manual Testing with cURL

```bash
# Health check
curl http://localhost:8000/health

# Extract from image
curl -X POST http://localhost:8000/extract/image \
  -F "file=@receipt.png" \
  -o result.json

# Extract from text
curl -X POST http://localhost:8000/extract/text \
  -H "Content-Type: application/json" \
  -d '{"ocr_texts": ["โรงพยาบาล", "HN: 123456"]}' \
  -o result.json
```

---

## Performance

### Typical Response Times

| Endpoint | Average Time | Notes |
|----------|--------------|-------|
| /health | < 50ms | Instant |
| /extract/text | 35-40s | AI extraction time |
| /extract/image | 36-42s | OCR + AI extraction |
| /extract/batch | 36s × N | N = number of images |

### Optimization Tips

1. **Use /extract/text** if you already have OCR results
2. **Batch processing** is more efficient for multiple documents
3. **Monitor** AI debug files to optimize prompts
4. **Increase timeout** in config.json if needed

---

## Configuration

Edit `config.json` to customize:

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

## Examples

### Complete Python Example

```python
import requests
import json

# API base URL
API_URL = "http://localhost:8000"

# 1. Check health
health = requests.get(f"{API_URL}/health").json()
print(f"API Status: {health['status']}")

# 2. Extract from image
with open('receipt.png', 'rb') as f:
    files = {'file': f}
    response = requests.post(f"{API_URL}/extract/image", files=files)
    result = response.json()

if result['success']:
    data = result['data']
    doc_info = data['extracted_data']['document_info']
    
    # Get hospital name
    hospital = next((item['value'] for item in doc_info 
                    if item['code'] == 'hospital_name'), None)
    print(f"Hospital: {hospital}")
    
    # Get billing items
    billing = next((item['value'] for item in doc_info 
                   if item['code'] == 'billing_items'), [])
    print(f"Billing Items: {len(billing)}")
    
    # Save result
    with open('result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
else:
    print(f"Error: {result['error']}")

# 3. Get statistics
stats = requests.get(f"{API_URL}/stats").json()
print(f"Success Rate: {stats['pipeline_stats'].get('success_rate', 0)*100}%")
```

---

## Swagger UI

Interactive API documentation available at:
**http://localhost:8000/docs**

Features:
- Try out endpoints directly
- See request/response schemas
- Download OpenAPI specification

---

## Support

For issues or questions:
1. Check AI debug files in `./output/ai_debug/`
2. Review logs in `./logs/pipeline.log`
3. Test with `test_api.py` script
4. Check Swagger docs at `/docs`

---

## Changelog

### v1.0.0 (2025-10-03)
- Initial release
- Two-Step AI Pipeline
- Image and text extraction
- Batch processing
- AI request/response debugging
- REST API with FastAPI

