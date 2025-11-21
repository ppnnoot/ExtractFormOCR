# 🔧 OneOCR Setup Guide

## 📋 Prerequisites

### Required Files
1. **`oneocr.dll`** - OneOCR Windows DLL
2. **`oneocr.onemodel`** - OneOCR model file

### File Placement
```
ExtractForm/
├── oneocr.dll          # OneOCR DLL file
├── oneocr.onemodel     # OneOCR model file
├── multi_ocr_adapter.py
├── complete_ai_pipeline.py
└── ...
```

## 🚀 Quick Setup

### 1. Copy Files
```bash
# Copy OneOCR files to project root directory
cp /path/to/oneocr.dll .
cp /path/to/oneocr.onemodel .
```

### 2. Test OneOCR
```python
# Test OneOCR directly
python examples/test_oneocr.py
```

### 3. Run Pipeline
```python
from complete_ai_pipeline import CompleteAIPipeline

pipeline = CompleteAIPipeline('config.json')
result = pipeline.process_document('your_image.jpg', 'invoice', 'hybrid')
```

## ⚙️ Configuration

OneOCR is configured in `config.json`:

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
  }
}
```

## 🔍 Features

### ✅ What's Implemented
- **DLL Loading**: Automatic OneOCR DLL loading
- **Model Loading**: OneOCR model initialization
- **Image Processing**: Support for various image formats
- **Text Recognition**: Line-by-line text extraction
- **Error Handling**: Comprehensive error handling
- **Logging**: Detailed logging for debugging

### ⚠️ Limitations
- **Bounding Boxes**: OneOCR doesn't provide exact bounding boxes (using estimated values)
- **Confidence Scores**: OneOCR doesn't provide confidence scores (using default 0.95)
- **Windows Only**: OneOCR is Windows-specific

## 🧪 Testing

### Test OneOCR Directly
```python
from multi_ocr_adapter import OneOCREngine

# Initialize
oneocr = OneOCREngine("./oneocr.dll", "./oneocr.onemodel")
oneocr.initialize()

# Recognize text
results = oneocr.recognize("test_image.jpg")
for result in results:
    print(f"Text: {result.text}")
```

### Test via Pipeline
```python
from complete_ai_pipeline import CompleteAIPipeline

pipeline = CompleteAIPipeline('config.json')
result = pipeline.process_document('test_image.jpg', 'invoice', 'rule')
```

## 🐛 Troubleshooting

### Common Issues

#### 1. DLL Not Found
```
Error: OneOCR DLL not found: ./oneocr.dll
```
**Solution**: Ensure `oneocr.dll` is in the project root directory

#### 2. Model Not Found
```
Error: OneOCR model not found: ./oneocr.onemodel
```
**Solution**: Ensure `oneocr.onemodel` is in the project root directory

#### 3. Import Error
```
Error: OneOCR not available - ctypes not found
```
**Solution**: OneOCR requires ctypes which is built into Python

#### 4. Windows Only
```
Error: OneOCR only works on Windows
```
**Solution**: Use OneOCR on Windows system or fallback to EasyOCR/PaddleOCR

### Debug Mode

Enable debug logging:

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

## 📊 Performance

### Expected Performance
- **Initialization**: 2-5 seconds (first time)
- **Text Recognition**: 1-3 seconds per document
- **Memory Usage**: ~100-200MB (model loaded)

### Optimization Tips
1. **Keep model loaded**: OneOCR loads model once and reuses
2. **Batch processing**: Process multiple images in sequence
3. **Image preprocessing**: Optimize images before OCR

## 🔄 Integration with Pipeline

OneOCR integrates seamlessly with the complete pipeline:

### 1. OCR Only
```python
pipeline = CompleteAIPipeline('config.json')
results = pipeline.ocr_manager.recognize('image.jpg', 'oneocr')
```

### 2. With Spatial Analysis
```python
pipeline = CompleteAIPipeline('config.json')
result = pipeline.process_document('image.jpg', 'invoice', 'rule')
```

### 3. With AI Extraction
```python
pipeline = CompleteAIPipeline('config.json')
result = pipeline.process_document('image.jpg', 'invoice', 'hybrid')
```

## 📈 Output Format

OneOCR returns standardized `OCRResult` objects:

```python
[
  OCRResult(
    text="Invoice No:",
    confidence=0.95,
    bbox=[[0, 0], [100, 0], [100, 20], [0, 20]],
    position={"x": 0, "y": 0, "width": 100, "height": 20}
  ),
  # ... more results
]
```

## 🎯 Best Practices

### 1. File Organization
- Keep OneOCR files in project root
- Use consistent naming (oneocr.dll, oneocr.onemodel)

### 2. Error Handling
- Always check initialization success
- Handle DLL loading errors gracefully
- Use fallback engines if OneOCR fails

### 3. Performance
- Initialize once and reuse
- Process images in batches
- Monitor memory usage

### 4. Testing
- Test with various image formats
- Verify text recognition accuracy
- Test error scenarios

## 🔧 Advanced Configuration

### Custom Model Path
```python
oneocr = OneOCREngine(
    dll_path="./libs/oneocr.dll",
    model_path="./models/oneocr.onemodel"
)
```

### Environment Setup
```python
import os
os.environ["path"] = "./libs" + os.pathsep + os.environ["path"]
```

## 📚 API Reference

### OneOCREngine

#### Methods
- `__init__(dll_path, model_path)`: Initialize engine
- `initialize()`: Load DLL and model
- `recognize(image)`: Recognize text in image
- `_prepare_image(image)`: Prepare image for processing
- `_setup_function_prototypes()`: Setup DLL function prototypes

#### Properties
- `initialized`: Whether engine is initialized
- `oneocr`: DLL instance
- `script_dir`: Script directory path

---

**OneOCR is now integrated and ready to use! 🎉**
