# 🎯 Master Prompts สำหรับสร้าง AI-Powered OCR Pipeline

## 📌 Prompt 1: Project Overview & Architecture

```
ฉันต้องการสร้างระบบ OCR Pipeline สำหรับองค์กร โดยมี requirements ดังนี้:

## Requirements:
1. ใช้ OneOCR (Windows) สำหรับ OCR - มี DLL และ Model file อยู่แล้ว
2. วิเคราะห์ spatial layout (x, y, bounding box) ของข้อความ
3. ส่งข้อมูล OCR พร้อม spatial info ไปให้ AI วิเคราะห์และ extract
4. Export ข้อมูลเป็น JSON ตาม template ที่กำหนด
5. มี fallback เป็น rule-based extraction ถ้า AI ล้มเหลว

## Technical Stack:
- OCR: OneOCR (Windows DLL)
- Language: Python 3.9+
- AI API: http://10.5.19.205:8080/v1/chat/completions (OpenAI compatible)
- Model: openai/gpt-oss-20b

## Features ที่ต้องการ:
1. Multi-OCR engine support (OneOCR, EasyOCR, PaddleOCR)
2. Spatial analysis (x, y coordinates, bounding boxes)
3. AI-powered extraction with LLM
4. Template-based extraction (custom JSON output)
5. Hybrid mode (AI + Rule-based fallback)
6. Batch processing
7. Statistics and monitoring

## Architecture:
```
OneOCR → OCR Results (text + bbox) → Spatial Analysis → AI/Rule Extraction → JSON Template → Output
```

กรุณาออกแบบ:
1. System architecture
2. Class structure
3. Data flow
4. API interfaces
5. Configuration format

และเขียนโค้ดตัวอย่างแต่ละส่วน
```

---

## 📌 Prompt 2: OneOCR Integration

```
ฉันมีไฟล์ OneOCR DLL สำหรับ Windows OCR โดยมีโค้ดตัวอย่างดังนี้:

[วาง code ที่คุณให้มาในเอกสาร]

กรุณาสร้าง:

1. **OCR Adapter Class** ที่:
   - Wrap OneOCR DLL calls
   - รองรับ OCR engines อื่นๆ (EasyOCR, PaddleOCR, Tesseract)
   - Fallback mechanism
   - Unified output format

2. **Output Format:**
```python
[
  {
    "text": "Invoice No:",
    "confidence": 0.92,
    "bbox": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
    "position": {"x": int, "y": int, "width": int, "height": int}
  }
]
```

3. **Features:**
   - Auto-detect best available OCR engine
   - Preprocessing (denoise, enhance)
   - Error handling และ retry logic
   - Performance monitoring

เขียนโค้ดที่:
- Modular และ extensible
- มี type hints
- มี docstrings
- รองรับ async operations (ถ้าเป็นไปได้)
```

---

## 📌 Prompt 3: Spatial Analysis

```
สร้างระบบ Spatial Analysis สำหรับวิเคราะห์ layout จาก OCR results โดยใช้:

## Input:
```python
ocr_results = [
  {"text": "Invoice No:", "bbox": [[50,120], [200,120], ...], "confidence": 0.9},
  {"text": "INV-001", "bbox": [[210,120], [400,120], ...], "confidence": 0.92}
]
```

## ต้องการ Features:

1. **Layout Analysis:**
   - จัดกลุ่ม text เป็น lines (ใช้ y-coordinate)
   - ตรวจจับ columns (ใช้ x-coordinate)
   - หา text blocks ที่เกี่ยวข้องกัน

2. **Spatial Relationships:**
   - `find_text_right_of(label)` - หา value ที่อยู่ด้านขวา label
   - `find_text_below(label)` - หา value ที่อยู่ด้านล่าง
   - `find_text_at_position(x, y, radius)` - หา text ใกล้พิกัดที่กำหนด

3. **Table Detection:**
   - ตรวจจับโครงสร้างตาราง
   - แยก header, data rows
   - Extract เป็น list of dicts

4. **Visualization:**
   - วาด bounding boxes บนรูปภาพ
   - แสดง spatial relationships
   - เซฟเป็นไฟล์สำหรับ debug

## Parameters:
- `line_threshold`: 20 pixels (text ที่ y ห่างกันไม่เกินนี้ = บรรทัดเดียวกัน)
- `column_threshold`: 50 pixels (text ที่ x ห่างกันไม่เกินนี้ = คอลัมน์เดียวกัน)

เขียนโค้ดที่:
- Efficient (ใช้ numpy ถ้าเหมาะสม)
- Configurable thresholds
- มี unit tests
```

---

## 📌 Prompt 4: AI Extraction Engine

```
สร้าง AI-powered extraction engine ที่ส่ง OCR results พร้อม spatial layout ไปให้ LLM วิเคราะห์

## AI API Specification:
```json
{
  "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
  "method": "POST",
  "headers": {"Content-Type": "application/json"},
  "body": {
    "model": "openai/gpt-oss-20b",
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": "..."}
    ],
    "temperature": 0.1,
    "max_tokens": 2000,
    "stream": false
  }
}
```

## Requirements:

1. **Prompt Engineering:**
   - สร้าง prompt ที่ส่ง OCR results พร้อม x, y coordinates
   - อธิบาย spatial relationships (same line, same column)
   - กำหนด fields ที่ต้องการ extract ตาม template
   - ขอ output เป็น JSON เท่านั้น

2. **Prompt Template:**
```
คุณเป็น AI expert ในการ extract ข้อมูลจากเอกสาร

# OCR Results (with spatial layout):
[... text blocks with x, y, bbox ...]

# Fields to Extract:
- invoice_number (required)
- date (required)
- total_amount (required)

# Spatial Analysis Tips:
- Text ที่ y ใกล้กัน (±20px) = same line
- Value มักอยู่ขวา label (x มากกว่า)
- Text ที่ x ใกล้กัน (±50px) = same column

Return ONLY JSON with extracted fields.
```

3. **Response Parsing:**
   - Parse JSON จาก AI response
   - Handle ```json``` code blocks
   - Validate output structure
   - Error recovery

4. **Quality Assessment:**
   - ประเมินคุณภาพของข้อมูลที่ extract ได้
   - ตรวจสอบ required fields
   - คำนวณ confidence score

เขียนโค้ดที่:
- Robust error handling
- Retry logic with exponential backoff
- Request/response logging
- Timeout handling
```

---

## 📌 Prompt 5: Template System

```
สร้างระบบ Template-based Extraction ที่รองรับ custom JSON templates

## Template Format:
```json
{
  "name": "invoice",
  "description": "Template for invoice extraction",
  "fields": {
    "invoice_number": {
      "description": "Invoice number",
      "required": true,
      "type": "string",
      "method": "spatial_right",
      "config": {
        "label": "Invoice No",
        "max_distance": 200,
        "line_tolerance": 20
      },
      "post_process": "trim"
    },
    "date": {
      "description": "Invoice date",
      "required": true,
      "type": "date",
      "method": "pattern",
      "config": {
        "pattern": "\\d{1,2}/\\d{1,2}/\\d{4}"
      },
      "post_process": "extract_date"
    }
  },
  "output_structure": {
    "document_type": "invoice",
    "extracted_at": "@now",
    "invoice": {
      "number": "${invoice_number}",
      "date": "${date}",
      "total": "${total_amount}"
    }
  }
}
```

## Extraction Methods:
1. **spatial_right**: หา value ด้านขวา label
2. **spatial_below**: หา value ด้านล่าง
3. **pattern**: Regular expression matching
4. **position**: Extract จากตำแหน่งแน่นอน (x, y)
5. **table**: Extract ตาราง
6. **first_match**: หา text แรกที่มี keyword

## Post-processing:
- trim, uppercase, lowercase
- remove_spaces, remove_currency
- extract_numbers, extract_date

## Requirements:
1. Template Manager (load, save, list templates)
2. Template-based Extractor
3. JSON Output Generator (รองรับ placeholders: ${field}, @now, @uuid)
4. Validation

เขียนโค้ดที่:
- Flexible และ extensible
- Support complex nested structures
- Custom post-processors
```

---

## 📌 Prompt 6: Hybrid Extraction Pipeline

```
สร้าง Hybrid Extraction Pipeline ที่รวม AI และ Rule-based

## Workflow:
```
OCR → Spatial Analysis → Try AI → Quality Check
                              ↓           ↓
                          Success?    Pass: Return AI result
                              ↓           ↓
                          Fail/Low    Fail: Fallback to Rule-based
                              ↓
                      Rule-based Extraction → Return
```

## Requirements:

1. **Extraction Modes:**
   - `ai`: ใช้ AI เท่านั้น
   - `rule`: ใช้ Rule-based เท่านั้น
   - `hybrid`: Try AI first, fallback to rule-based

2. **Quality Assessment:**
   - ตรวจสอบ required fields ครบหรือไม่
   - คำนวณ completeness score
   - Configurable quality threshold (default: 0.5)

3. **Fallback Logic:**
```python
if ai_quality_score >= threshold:
    return ai_result, "ai"
else:
    return rule_based_result, "rule"
```

4. **Statistics:**
   - Track ai_success, ai_failed, rule_fallback
   - Performance metrics (time, accuracy)
   - Success rates

5. **Configuration:**
```json
{
  "extraction": {
    "mode": "hybrid",
    "ai_quality_threshold": 0.5,
    "prefer_ai": true
  }
}
```

เขียน Complete Pipeline ที่:
- รองรับทั้ง single document และ batch processing
- Configurable
- Monitoring และ logging
- Error recovery
```

---

## 📌 Prompt 7: Complete Integration

```
รวมทุก component เข้าด้วยกันเป็น Complete System:

## Components:
1. OCR Manager (multi-engine support)
2. Spatial Analyzer (layout analysis)
3. AI Extraction Engine (LLM integration)
4. Template Manager (custom templates)
5. Hybrid Pipeline (AI + Rule-based)
6. JSON Output Generator

## Main Pipeline Flow:
```python
def process_document(image_path, template_name, mode):
    # 1. OCR
    ocr_results = ocr_manager.recognize(image_path)
    
    # 2. Spatial Analysis (optional, for rule-based)
    spatial_info = spatial_analyzer.analyze(ocr_results)
    
    # 3. Load Template
    template = template_manager.load(template_name)
    
    # 4. Extract (AI or Rule or Hybrid)
    if mode == "ai":
        data = ai_engine.extract(ocr_results, template)
    elif mode == "rule":
        data = rule_extractor.extract(ocr_results, template)
    else:  # hybrid
        data, method = hybrid_engine.extract(ocr_results, template)
    
    # 5. Generate JSON Output
    output = json_generator.generate(data, template)
    
    # 6. Save
    save_output(output)
    
    return output
```

## Features:
1. Configuration management (JSON config file)
2. CLI interface
3. Python API
4. Batch processing
5. Statistics and reporting
6. Debug modes (save raw OCR, AI prompts)
7. Error handling

## File Structure:
```
project/
├── multi_ocr_adapter.py
├── spatial_ocr_extraction.py
├── template_extraction_system.py
├── ai_powered_extraction.py
├── complete_ai_pipeline.py  # Main
├── config.json
├── templates/
│   ├── invoice.json
│   └── receipt.json
└── output/
    ├── json/
    └── raw_ocr/
```

เขียนโค้ดที่:
- Production-ready
- Well-documented
- Unit tested
- Performance optimized
```

---

## 📌 Prompt 8: Testing & Examples

```
สร้าง comprehensive tests และ examples:

## 1. Unit Tests:
```python
# test_ocr_adapter.py
def test_oneocr_recognition():
    manager = OCRManager(engine_type='oneocr')
    results = manager.recognize('test_invoice.jpg')
    assert len(results) > 0
    assert 'text' in results[0]
    assert 'bbox' in results[0]

# test_spatial_analysis.py
def test_find_text_right_of():
    analyzer = SpatialOCRAnalyzer()
    analyzer.load_ocr_results(mock_data)
    value = analyzer.find_text_right_of(reference_block)
    assert value is not None

# test_ai_extraction.py
def test_ai_extract():
    engine = AIExtractionEngine()
    result = engine.extract(mock_ocr, mock_template)
    assert 'invoice_number' in result
```

## 2. Integration Tests:
```python
def test_complete_pipeline():
    pipeline = CompleteAIPipeline()
    result = pipeline.process_document(
        'test_invoice.jpg',
        template_name='invoice',
        extraction_mode='hybrid'
    )
    assert result['document_type'] == 'invoice'
    assert 'invoice_number' in result['invoice']
```

## 3. Mock Data:
สร้าง mock OCR results สำหรับ testing

## 4. Example Scripts:
- Basic usage
- Custom template creation
- Batch processing
- API integration

## 5. Documentation:
- README.md
- API documentation
- Configuration guide
- Troubleshooting guide
```

---

## 📌 Prompt 9: Production Optimization

```
Optimize สำหรับ production deployment:

## Performance:
1. **Caching:**
   - Cache AI responses (based on OCR results hash)
   - Cache template parsing
   - LRU cache for frequently accessed templates

2. **Multiprocessing:**
   - Batch processing with ProcessPoolExecutor
   - Async API calls
   - Queue-based processing

3. **Resource Management:**
   - Connection pooling for API calls
   - Memory optimization
   - Cleanup temporary files

## Monitoring:
1. **Metrics:**
   - Processing time per document
   - AI success rate
   - Error rates
   - API latency

2. **Logging:**
   - Structured logging (JSON)
   - Different log levels
   - Rotation

3. **Alerting:**
   - High error rate
   - Slow processing
   - AI API failures

## API Service:
```python
from fastapi import FastAPI, UploadFile

app = FastAPI()
pipeline = CompleteAIPipeline()

@app.post("/api/extract")
async def extract(file: UploadFile, template: str = "invoice"):
    result = pipeline.process_document(file, template)
    return result
```

## Docker:
```dockerfile
FROM python:3.9
COPY . /app
RUN pip install -r requirements.txt
CMD ["python", "complete_ai_pipeline.py"]
```

เขียนโค้ดที่:
- Scalable
- Maintainable
- Observable
- Secure
```

---

## 📌 Prompt 10: Documentation & Examples

```
สร้าง comprehensive documentation:

## 1. README.md:
- Project overview
- Quick start (3 steps)
- Installation
- Basic usage examples
- Configuration

## 2. User Guide:
- Detailed feature documentation
- Template creation guide
- Best practices
- Common use cases

## 3. API Documentation:
- All classes and methods
- Parameters and return values
- Code examples
- Error handling

## 4. Troubleshooting Guide:
- Common issues
- Debug techniques
- Performance tips

## 5. Examples:
- Basic extraction
- Custom templates
- Batch processing
- API integration
- Production deployment

รวมถึง:
- Architecture diagrams
- Flow charts
- Example outputs
- Screenshots (ถ้าเป็นไปได้)
```

---

## 🎯 Prompt สำหรับ Custom Templates

```
สร้าง template สำหรับเอกสาร [ประเภท] ที่มี layout ดังนี้:

[อธิบาย layout หรือแนบรูปภาพ]

Fields ที่ต้องการ extract:
1. [field1] - อยู่ที่ [ตำแหน่ง] - [รูปแบบ]
2. [field2] - อยู่ที่ [ตำแหน่ง] - [รูปแบบ]
...

JSON output structure ที่ต้องการ:
```json
{
  "document_type": "...",
  "data": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

สร้าง:
1. Template JSON
2. Example usage code
3. Test cases
```

---

## 🚀 Quick Reference Commands

### สร้างระบบใหม่ทั้งหมด:
```
ใช้ Prompt 1-7 ตามลำดับ
```

### เพิ่ม OCR engine ใหม่:
```
ใช้ Prompt 2 + ระบุ engine ที่ต้องการ
```

### สร้าง custom template:
```
ใช้ Prompt สำหรับ Custom Templates
```

### Optimize performance:
```
ใช้ Prompt 9
```

### Deploy to production:
```
ใช้ Prompt 9 + 10
```

---

## 💡 Tips for Better Results

1. **Be Specific:**
   - ให้รายละเอียด requirements ชัดเจน
   - แนบตัวอย่างโค้ดหรือข้อมูล
   - ระบุ edge cases

2. **Iterate:**
   - เริ่มจาก high-level architecture
   - จากนั้นค่อยลงรายละเอียด
   - Test และ refine

3. **Provide Context:**
   - บอกว่าจะใช้งานอย่างไร
   - มี constraints อะไรบ้าง
   - ต้องการ features อะไรเป็นพิเศษ

4. **Ask for Alternatives:**
   - "มีวิธีอื่นที่ดีกว่าไหม?"
   - "ข้อดี-ข้อเสียของแต่ละวิธี?"

---

## 📚 Follow-up Prompts

หลังจากได้โค้ดแล้ว:

```
"เพิ่ม error handling และ logging"
"เพิ่ม unit tests"
"Optimize performance"
"เพิ่ม type hints และ docstrings"
"สร้าง API documentation"
"เพิ่ม configuration options"
"Handle edge cases: [ระบุ case]"
```