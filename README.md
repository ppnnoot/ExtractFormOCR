# 🚀 AI-Powered OCR Pipeline

ระบบ OCR Pipeline ที่ใช้ AI และ Rule-based extraction สำหรับการประมวลผลเอกสารอัตโนมัติ

## ✨ Features

- **Multi-OCR Engine Support**: รองรับ OneOCR (Windows DLL), EasyOCR, PaddleOCR พร้อม fallback mechanism
- **OneOCR Integration**: Native Windows DLL integration สำหรับประสิทธิภาพสูงสุด
- **Spatial Analysis**: วิเคราะห์ layout และความสัมพันธ์ของข้อความ (x, y coordinates)
- **AI-Powered Extraction**: ใช้ LLM ในการ extract ข้อมูลอย่างชาญฉลาด
- **Template System**: รองรับ custom JSON templates สำหรับ output format
- **Hybrid Mode**: รวม AI และ Rule-based extraction พร้อม fallback
- **Batch Processing**: ประมวลผลหลายเอกสารพร้อมกัน
- **Statistics & Monitoring**: ติดตาม performance และ success rate

## 🏗️ Architecture

```
OCR → Spatial Analysis → AI/Rule Extraction → JSON Template → Output
```

### Components

1. **MultiOCRManager**: จัดการ OCR engines หลายตัว
2. **SpatialOCRAnalyzer**: วิเคราะห์ spatial layout
3. **AIExtractionEngine**: AI-powered extraction
4. **TemplateManager**: จัดการ templates
5. **TemplateExtractor**: Rule-based extraction
6. **CompleteAIPipeline**: Main pipeline

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd ExtractForm

# Install dependencies
pip install -r requirements.txt
```

### 2. OneOCR Setup (Required)

วางไฟล์ OneOCR ใน project root:
```
ExtractForm/
├── oneocr.dll          # OneOCR DLL file
├── oneocr.onemodel     # OneOCR model file
└── ...
```

ดูรายละเอียดเพิ่มเติมใน [ONECR_SETUP.md](ONECR_SETUP.md)

### 3. Configuration

แก้ไข `config.json` ตามความต้องการ:

```json
{
  "ocr": {
    "engines": {
      "oneocr": {
        "enabled": true,
        "priority": 1,
        "dll_path": "./oneocr.dll",
        "model_path": "./oneocr.onemodel"
      }
    }
  },
  "ai_extraction": {
    "api": {
      "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
      "model": "openai/gpt-oss-20b"
    }
  }
}
```

### 4. Basic Usage

```python
from complete_ai_pipeline import CompleteAIPipeline

# Initialize pipeline
pipeline = CompleteAIPipeline('config.json')

# Process single document
result = pipeline.process_document('invoice.jpg', 'invoice', 'hybrid')

if result['success']:
    print(f"Extracted data: {result['data']}")
    print(f"Processing time: {result['processing_time']:.2f}s")
```

### 5. Command Line Interface

```bash
# Process single image
python complete_ai_pipeline.py invoice.jpg --template invoice --mode hybrid

# Process directory
python complete_ai_pipeline.py ./images/ --template invoice

# Show statistics
python complete_ai_pipeline.py invoice.jpg --stats
```

## 📋 Supported Document Types

### Default Templates

- **Invoice**: ใบแจ้งหนี้
- **Receipt**: ใบเสร็จ
- **ID Card**: บัตรประชาชน (Thai)

### Custom Templates

สร้าง template ใหม่ได้โดยใช้ JSON format:

```json
{
  "name": "custom_template",
  "description": "Custom document template",
  "fields": {
    "field_name": {
      "description": "Field description",
      "required": true,
      "method": "spatial_right",
      "config": {
        "label": "Label text",
        "max_distance": 200
      },
      "post_process": "trim,uppercase"
    }
  },
  "output_structure": {
    "document_type": "custom",
    "data": {
      "field": "${field_name}"
    }
  }
}
```

## 🔧 Extraction Methods

### 1. Spatial Methods
- `spatial_right`: หาค่าที่อยู่ด้านขวาของ label
- `spatial_below`: หาค่าที่อยู่ด้านล่างของ label
- `position`: Extract จากตำแหน่งแน่นอน

### 2. Pattern Methods
- `pattern`: ใช้ regex pattern matching
- `first_match`: หาข้อความแรกที่มี keyword

### 3. Table Methods
- `table`: Extract ข้อมูลจากตาราง

### 4. Post-processing
- `trim`: ตัด whitespace
- `uppercase/lowercase`: เปลี่ยนตัวพิมพ์
- `extract_numbers`: ดึงเฉพาะตัวเลข
- `extract_date`: แปลงรูปแบบวันที่
- `remove_currency`: ลบสัญลักษณ์เงิน

## 🎯 Extraction Modes

### 1. AI Mode
ใช้ AI เท่านั้นในการ extract ข้อมูล

```python
result = pipeline.process_document('doc.jpg', 'invoice', 'ai')
```

### 2. Rule Mode
ใช้ Rule-based extraction เท่านั้น

```python
result = pipeline.process_document('doc.jpg', 'invoice', 'rule')
```

### 3. Hybrid Mode (Recommended)
ใช้ AI ก่อน ถ้าคุณภาพต่ำเกินไปจึง fallback เป็น rule-based

```python
result = pipeline.process_document('doc.jpg', 'invoice', 'hybrid')
```

## 📊 Output Format

```json
{
  "document_type": "invoice",
  "extracted_at": "2024-01-15 10:30:00",
  "invoice": {
    "number": "INV-001",
    "date": "2024-01-15",
    "total": "1250.00"
  },
  "_metadata": {
    "document_id": "uuid-string",
    "template_name": "invoice",
    "extraction_method": "ai",
    "processing_time": 2.5,
    "text_blocks_count": 15
  }
}
```

## 📈 Statistics & Monitoring

```python
# Get pipeline statistics
stats = pipeline.get_statistics()
print(f"Success rate: {stats['success_rate']:.1%}")
print(f"Average processing time: {stats['avg_processing_time']:.2f}s")
print(f"AI success rate: {stats['ai_success_rate']:.1%}")
```

## 🔧 Configuration Options

### OCR Settings
```json
{
  "ocr": {
    "engines": {
      "oneocr": {
        "enabled": true,
        "priority": 1,
        "dll_path": "./oneocr.dll",
        "model_path": "./oneocr.onemodel"
      },
      "easyocr": {"enabled": false, "priority": 2},
      "paddleocr": {"enabled": false, "priority": 3}
    },
    "preprocessing": {
      "denoise": true,
      "enhance": true,
      "deskew": true
    }
  }
}
```

## 🔧 OneOCR Integration

### Setup OneOCR
1. **Copy files**: `oneocr.dll` และ `oneocr.onemodel` ไปยัง project root
2. **Test**: รัน `python examples/test_oneocr.py`
3. **Configure**: ตั้งค่าใน `config.json` ให้ `oneocr.enabled = true`

### OneOCR Features
- **Native Windows DLL**: ประสิทธิภาพสูง
- **High Accuracy**: การจดจำข้อความแม่นยำ
- **Fast Processing**: ประมวลผลเร็ว
- **Automatic Fallback**: ใช้ engine อื่นถ้า OneOCR ล้มเหลว

### OneOCR Limitations
- **Windows Only**: ทำงานได้เฉพาะ Windows
- **No Bounding Boxes**: ไม่มีตำแหน่งข้อความที่แน่นอน (ใช้ค่าประมาณ)
- **No Confidence Scores**: ไม่มีคะแนนความเชื่อมั่น (ใช้ค่า default)

### Spatial Analysis
```json
{
  "spatial_analysis": {
    "line_threshold": 20,
    "column_threshold": 50,
    "table_detection": {
      "enabled": true,
      "min_cells": 4
    }
  }
}
```

### AI Extraction
```json
{
  "ai_extraction": {
    "api": {
      "endpoint": "http://your-ai-api.com/v1/chat/completions",
      "model": "your-model",
      "temperature": 0.1,
      "max_tokens": 2000
    },
    "quality_threshold": 0.5
  }
}
```

## 🧪 Testing

```bash
# Run unit tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_pipeline.py::TestCompletePipeline -v
```

## 📝 Examples

ดูตัวอย่างการใช้งานใน `examples/` directory:

- `basic_usage.py`: การใช้งานพื้นฐาน
- `custom_templates.py`: การสร้าง custom templates
- `batch_processing.py`: การประมวลผลแบบ batch

## 🚀 Advanced Usage

### Batch Processing
```python
image_paths = ['doc1.jpg', 'doc2.jpg', 'doc3.jpg']
results = pipeline.batch_process(image_paths, 'invoice', 'hybrid')

for i, result in enumerate(results):
    print(f"Document {i+1}: {'✅' if result['success'] else '❌'}")
```

### Custom Template Creation
```python
template = {
    "name": "receipt",
    "fields": {
        "total": {
            "method": "pattern",
            "config": {"pattern": r'\$[\d,]+\.?\d*'}
        }
    }
}

pipeline.create_template("receipt", template)
```

### Engine Information
```python
info = pipeline.get_engine_info()
print(f"Available OCR engines: {info['ocr_engines']}")
print(f"AI cache stats: {info['ai_cache_stats']}")
```

## 🛠️ Troubleshooting

### Common Issues

1. **OCR Recognition Failed**
   - ตรวจสอบว่าไฟล์รูปภาพมีอยู่และสามารถอ่านได้
   - ลองใช้ OCR engine อื่น
   - ตรวจสอบ preprocessing settings

2. **AI API Connection Failed**
   - ตรวจสอบ endpoint URL และ network connection
   - ตรวจสอบ API key (ถ้ามี)
   - ลองใช้ rule-based mode

3. **Template Not Found**
   - ตรวจสอบว่า template file มีอยู่ใน `templates/` directory
   - ตรวจสอบ JSON format ของ template

4. **Low Extraction Accuracy**
   - ปรับ spatial thresholds ใน config
   - ปรับ AI prompt หรือ temperature
   - ใช้ hybrid mode สำหรับ fallback

### Debug Mode

เปิด debug logging เพื่อดูรายละเอียด:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## 📚 API Reference

### CompleteAIPipeline

#### Methods

- `process_document(image_path, template_name, extraction_mode)`: ประมวลผลเอกสารเดียว
- `batch_process(image_paths, template_name, extraction_mode)`: ประมวลผลหลายเอกสาร
- `get_statistics()`: ดึงสถิติการประมวลผล
- `get_available_templates()`: ดึงรายการ templates
- `create_template(name, config)`: สร้าง template ใหม่

### SpatialOCRAnalyzer

#### Methods

- `find_text_right_of(reference_text, max_distance, line_tolerance)`: หาข้อความด้านขวา
- `find_text_below(reference_text, max_distance, column_tolerance)`: หาข้อความด้านล่าง
- `find_text_at_position(x, y, radius)`: หาข้อความใกล้ตำแหน่ง
- `visualize(image_path, output_path)`: สร้าง visualization

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📄 License

MIT License

## 🙏 Acknowledgments

- OneOCR for Windows OCR capabilities
- EasyOCR and PaddleOCR for open-source OCR
- OpenAI-compatible API for AI extraction

---

**Happy Document Processing! 🎉**

