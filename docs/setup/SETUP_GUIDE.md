# 🚀 AI-Powered OCR Pipeline - Setup Guide

## ✅ สถานะการพัฒนา

ระบบ AI-Powered OCR Pipeline ได้ถูกพัฒนาครบถ้วนแล้ว! 🎉

### 📦 Components ที่สร้างเสร็จแล้ว

1. **✅ MultiOCRManager** (`multi_ocr_adapter.py`)
   - รองรับ OneOCR, EasyOCR, PaddleOCR
   - Auto-fallback mechanism
   - Unified output format
   - Error handling และ retry logic

2. **✅ SpatialOCRAnalyzer** (`spatial_ocr_extraction.py`)
   - วิเคราะห์ spatial layout (x, y coordinates)
   - จัดกลุ่ม text เป็น lines และ columns
   - ตรวจจับ table structures
   - Functions: find_text_right_of, find_text_below, find_text_at_position
   - Visualization support

3. **✅ AIExtractionEngine** (`ai_powered_extraction.py`)
   - Integration กับ AI API (OpenAI-compatible)
   - Prompt engineering สำหรับ OCR results
   - Response parsing และ validation
   - Quality assessment
   - Caching system

4. **✅ Template System** (`template_extraction_system.py`)
   - TemplateManager: load, save, validate templates
   - TemplateExtractor: rule-based extraction
   - JSONOutputGenerator: generate structured output
   - Post-processing functions
   - Multiple extraction methods

5. **✅ Complete Pipeline** (`complete_ai_pipeline.py`)
   - รวมทุก component เข้าด้วยกัน
   - รองรับ 3 modes: ai, rule, hybrid
   - Batch processing
   - Statistics และ monitoring
   - CLI interface
   - Error handling

6. **✅ Testing & Examples**
   - Unit tests (`tests/test_pipeline.py`)
   - Basic usage examples (`examples/basic_usage.py`)
   - Test data generator (`examples/create_test_data.py`)
   - Comprehensive documentation

## 🛠️ การติดตั้งและใช้งาน

### 1. Prerequisites

```bash
# Python 3.9+
python --version

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

แก้ไข `config.json` ตามความต้องการ:

```json
{
  "ai_extraction": {
    "api": {
      "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
      "model": "openai/gpt-oss-20b"
    }
  }
}
```

### 3. สร้างข้อมูลทดสอบ

```python
# รัน script สร้างข้อมูลทดสอบ
python examples/create_test_data.py
```

### 4. ทดสอบระบบ

```python
from complete_ai_pipeline import CompleteAIPipeline

# Initialize pipeline
pipeline = CompleteAIPipeline('config.json')

# Process document
result = pipeline.process_document('test_invoice.jpg', 'invoice', 'hybrid')

if result['success']:
    print(f"✅ Success: {result['data']}")
else:
    print(f"❌ Failed: {result['error']}")
```

### 5. Command Line Usage

```bash
# Process single image
python complete_ai_pipeline.py test_invoice.jpg --template invoice --mode hybrid

# Process directory
python complete_ai_pipeline.py ./images/ --template invoice

# Show statistics
python complete_ai_pipeline.py test_invoice.jpg --stats
```

## 📋 Features ที่พร้อมใช้งาน

### 🔍 OCR Capabilities
- **Multi-engine support**: OneOCR, EasyOCR, PaddleOCR
- **Auto-fallback**: หาก engine หนึ่งล้มเหลว จะลอง engine อื่น
- **Preprocessing**: denoise, enhance, deskew
- **Unified output**: format เดียวกันสำหรับทุก engine

### 🧠 AI Integration
- **LLM-powered extraction**: ใช้ AI วิเคราะห์และ extract ข้อมูล
- **Smart prompting**: ส่ง OCR results พร้อม spatial info
- **Quality assessment**: ประเมินคุณภาพของผลลัพธ์
- **Caching**: cache responses เพื่อเพิ่ม performance

### 📐 Spatial Analysis
- **Layout detection**: จัดกลุ่ม text เป็น lines และ columns
- **Relationship finding**: หาความสัมพันธ์ของข้อความ
- **Table detection**: ตรวจจับโครงสร้างตาราง
- **Visualization**: สร้างรูปแสดง spatial relationships

### 🎯 Template System
- **Flexible templates**: JSON-based configuration
- **Multiple methods**: spatial, pattern, position, table
- **Post-processing**: trim, uppercase, extract_numbers, etc.
- **Custom output**: กำหนดโครงสร้าง JSON output ได้

### 🔄 Hybrid Mode
- **AI-first approach**: ลอง AI ก่อน
- **Rule-based fallback**: ถ้า AI ล้มเหลว
- **Quality threshold**: กำหนดเกณฑ์คุณภาพ
- **Statistics tracking**: ติดตาม success rate

## 📊 Supported Document Types

### Default Templates
1. **Invoice** - ใบแจ้งหนี้
2. **Receipt** - ใบเสร็จ  
3. **ID Card** - บัตรประชาชน

### Custom Templates
สร้าง template ใหม่ได้ตามต้องการ:

```json
{
  "name": "custom_template",
  "fields": {
    "field_name": {
      "method": "spatial_right",
      "config": {"label": "Label"},
      "post_process": "trim,uppercase"
    }
  }
}
```

## 🎯 Extraction Modes

### 1. AI Mode
```python
result = pipeline.process_document('doc.jpg', 'invoice', 'ai')
```
- ใช้ AI เท่านั้น
- เหมาะสำหรับเอกสารที่ซับซ้อน
- ต้องการ AI API ที่ทำงานได้

### 2. Rule Mode
```python
result = pipeline.process_document('doc.jpg', 'invoice', 'rule')
```
- ใช้ Rule-based เท่านั้น
- เร็วและไม่ต้องใช้ AI API
- เหมาะสำหรับเอกสารที่มีรูปแบบแน่นอน

### 3. Hybrid Mode (แนะนำ)
```python
result = pipeline.process_document('doc.jpg', 'invoice', 'hybrid')
```
- ลอง AI ก่อน
- Fallback เป็น rule-based ถ้าจำเป็น
- ได้ความแม่นยำสูงและความเสถียร

## 📈 Monitoring & Statistics

```python
stats = pipeline.get_statistics()
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"AI success rate: {stats['ai_success_rate']:.1%}")
print(f"Average processing time: {stats['avg_processing_time']:.2f}s")
```

## 🔧 Configuration Options

### OCR Settings
```json
{
  "ocr": {
    "engines": {
      "oneocr": {"enabled": true, "priority": 1},
      "easyocr": {"enabled": true, "priority": 2},
      "paddleocr": {"enabled": true, "priority": 3}
    }
  }
}
```

### Spatial Analysis
```json
{
  "spatial_analysis": {
    "line_threshold": 20,
    "column_threshold": 50,
    "table_detection": {"enabled": true}
  }
}
```

### AI Extraction
```json
{
  "ai_extraction": {
    "api": {
      "endpoint": "http://your-api.com/v1/chat/completions",
      "model": "your-model",
      "temperature": 0.1
    },
    "quality_threshold": 0.5
  }
}
```

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/ -v

# Test specific component
python -m pytest tests/test_pipeline.py::TestCompletePipeline -v
```

## 📚 Examples

ดูตัวอย่างการใช้งานใน `examples/` directory:

- `basic_usage.py` - การใช้งานพื้นฐาน
- `create_test_data.py` - สร้างข้อมูลทดสอบ

## 🚀 Production Deployment

### 1. Performance Optimization
- เปิด caching ใน config
- ใช้ batch processing สำหรับหลายเอกสาร
- ปรับ OCR engine priorities

### 2. Monitoring
- เปิด logging level DEBUG
- ติดตาม statistics
- Monitor AI API performance

### 3. Error Handling
- ตั้ง fallback mechanisms
- Handle API failures gracefully
- Log errors สำหรับ debugging

## 🎉 สรุป

ระบบ AI-Powered OCR Pipeline พร้อมใช้งานแล้ว! 

### ✅ สิ่งที่ได้
- ระบบ OCR ที่รองรับหลาย engines
- AI-powered extraction ที่ชาญฉลาด
- Template system ที่ยืดหยุ่น
- Hybrid mode ที่เสถียร
- Monitoring และ statistics
- Testing และ examples ครบถ้วน

### 🚀 ต่อไป
- ติดตั้ง dependencies
- ปรับ config ตามความต้องการ
- ทดสอบกับเอกสารจริง
- สร้าง custom templates
- Deploy ใน production

**Happy Document Processing! 🎉**

