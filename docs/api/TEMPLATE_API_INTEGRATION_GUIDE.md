# 🔄 Template API Integration Guide

**วันที่:** 16 ตุลาคม 2568  
**คุณสมบัติ:** ดึง Template Configuration จาก API แทนไฟล์ JSON

---

## 📋 สรุป Executive Summary

### **ปัญหาเดิม:**
- Template ถูก hard-code ในไฟล์ JSON ภายใน project
- การแก้ไข template ต้อง redeploy ทั้งระบบ
- ไม่สามารถ update template แบบ real-time ได้
- ยากต่อการจัดการ template หลายฟอร์ม

### **โซลูชันใหม่:**
- ✅ **ดึง template จาก API แบบ dynamic**
- ✅ **Cache template เพื่อ performance**
- ✅ **Fallback to local files** กรณี API down
- ✅ **Security validation** ทุก API call
- ✅ **Auto-refresh cache** ตามเวลาที่กำหนด

---

## 🎯 ประโยชน์ที่ได้รับ

### **1. ความยืดหยุ่น (Flexibility)**
- อัพเดต template ได้โดยไม่ต้อง redeploy
- เพิ่มฟอร์มใหม่ได้ทันที
- แก้ไข field configuration แบบ real-time

### **2. ประสิทธิภาพ (Performance)**
- Cache template เพื่อลด API calls
- Configurable cache TTL (default 60 นาที)
- Refresh cache แบบ selective หรือ all

### **3. ความปลอดภัย (Security)**
- Validate API response structure
- Log ทุก API call ด้วย SecurityLogger
- Rate limiting และ retry mechanism
- Timeout protection

### **4. ความเสถียร (Reliability)**
- Fallback to local files อัตโนมัติ
- Retry mechanism (default 3 ครั้ง)
- Error handling ครอบคลุม
- Statistics และ monitoring

---

## 🏗️ สถาปัตยกรรม (Architecture)

```
┌─────────────────────────────────────────────────┐
│             APPLICATION LAYER                    │
│  (api_server.py, ai_simple_extraction.py)       │
└────────────────┬────────────────────────────────┘
                 │ get_template()
                 ▼
┌─────────────────────────────────────────────────┐
│        TEMPLATE API MANAGER                      │
│     (template_api_manager.py)                    │
│                                                   │
│  ┌─────────────────────────────────────┐        │
│  │  1. Check Cache                      │        │
│  │     └─> Cache Hit? Return            │        │
│  └─────────────────────────────────────┘        │
│                 │                                 │
│                 ▼ Cache Miss                      │
│  ┌─────────────────────────────────────┐        │
│  │  2. Fetch from API                   │        │
│  │     - Security Validation            │        │
│  │     - Retry Mechanism                │        │
│  │     - Parse Response                 │        │
│  └─────────────────────────────────────┘        │
│                 │                                 │
│                 ▼ Success                         │
│  ┌─────────────────────────────────────┐        │
│  │  3. Store in Cache                   │        │
│  │     - Set TTL                        │        │
│  │     - Update Statistics              │        │
│  └─────────────────────────────────────┘        │
│                 │                                 │
│                 ▼ API Failed                      │
│  ┌─────────────────────────────────────┐        │
│  │  4. Fallback to Local Files          │        │
│  │     - Load from ./templates/         │        │
│  │     - Update Statistics              │        │
│  └─────────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              EXTERNAL API                        │
│  https://ocr.rg.in.th/uapi/api/                 │
│      KOConfiguration-GetFormId                   │
└─────────────────────────────────────────────────┘
```

---

## 📡 API Specification

### **Endpoint:**
```
POST https://ocr.rg.in.th/uapi/api/KOConfiguration-GetFormId
```

### **Request:**
```json
{
  "Content-Type": "application/json"
}

Body: {}  (Empty JSON)
```

### **Response:**
```json
{
  "Successful": true,
  "Code": 200,
  "Message": "OK",
  "Description": "The resource has been fetched and is transmitted in the message body.",
  "Time": "2025-10-16 12:16:52",
  "data": [
    {
      "Id": 1,
      "formId": "HL0000050",
      "type": "DOCUMENT",
      "class": "IFlowDocument",
      "docName": "Receipt-Bill",
      "docThaiName": "Receipt-Bill",
      "docType": "Confidential Document",
      "docCat": "Supporting Document",
      "docSubCat": "Medical Non Form",
      "funcGroup": "[\"POS\",\"CLAIM\",\"HCO\",\"CCC\"]",
      "fileName": null,
      "isConvert": 0,
      "bpmsStatus": null,
      "doc_sequence": 0,
      "_version": 1,
      "IsActive": 0,
      "CreateDate": null,
      "UpdateDate": "2024-02-09T08:14:55Z",
      "sequence": 3,
      "sequence_clm": 1,
      "isExtraction": 1,
      "Template_json": "{\"documents\": [{\"page\": null, \"total_page\": null, \"document_code\": null, \"document_info\": [{\"code\": \"hospital_name\", \"page\": null, \"type\": \"string\", \"value\": null, \"accuracyRate\": null}, ...]}]}"
    }
  ]
}
```

---

## ⚙️ Configuration

### **config.json:**
```json
{
  "templates": {
    "api": {
      "url": "https://ocr.rg.in.th/uapi/api/KOConfiguration-GetFormId",
      "timeout": 30,
      "max_retries": 3,
      "enabled": true
    },
    "cache_enabled": true,
    "cache_ttl": 60,
    "fallback_enabled": true,
    "directory": "./templates",
    "default": "medical_receipt",
    "form_id_mapping": {
      "medical_receipt": "HL0000050",
      "receipt": "HL0000050",
      "invoice": "HL0000052",
      "detail": "HL0000053",
      "estimate": "HL0000054",
      "statement": "HL0000055",
      "endorsement": "NO00C0000"
    }
  }
}
```

### **Configuration Options:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api.url` | string | - | API endpoint URL |
| `api.timeout` | int | 30 | Request timeout (seconds) |
| `api.max_retries` | int | 3 | Max retry attempts |
| `api.enabled` | bool | true | Enable/disable API |
| `cache_enabled` | bool | true | Enable template caching |
| `cache_ttl` | int | 60 | Cache TTL (minutes) |
| `fallback_enabled` | bool | true | Enable fallback to files |
| `directory` | string | ./templates | Fallback directory |
| `default` | string | medical_receipt | Default template |
| `form_id_mapping` | object | - | Name to formId mapping |

---

## 💻 การใช้งาน (Usage)

### **1. Basic Usage:**

```python
from template_api_manager import TemplateAPIManager
import json

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize manager
manager = TemplateAPIManager(config)

# Get template
template = manager.get_template('medical_receipt')

if template:
    print(f"Form ID: {template['form_id']}")
    print(f"Document Type: {template['document_type']}")
    
    # Access template structure
    structure = template['template_structure']
    documents = structure['documents']
    
    # Get fields
    for doc in documents:
        fields = doc['document_info']
        for field in fields:
            print(f"Field: {field['code']}, Type: {field['type']}")
```

### **2. Integration with Existing Pipeline:**

```python
from ai_simple_extraction import TwoStepAIPipeline
from template_api_manager import TemplateAPIManager

# Initialize
config = load_config('config.json')
template_manager = TemplateAPIManager(config)
pipeline = TwoStepAIPipeline(config)

# Get template from API
template = template_manager.get_template('medical_receipt')

# Process document with template
result = pipeline.process_document(
    image_path='receipt.png',
    template='medical_receipt'
)
```

### **3. Cache Management:**

```python
# Refresh specific template
manager.refresh_cache('medical_receipt')

# Refresh all templates
manager.refresh_cache()

# Clear cache
manager.cache.clear()

# Get cache statistics
stats = manager.get_statistics()
print(f"Cache hits: {stats['cache_hits']}")
print(f"Cache misses: {stats['cache_misses']}")
```

### **4. Get All Templates:**

```python
# Fetch all available templates
all_templates = manager.get_all_templates()

for template in all_templates:
    print(f"{template['form_id']}: {template['document_type']}")
```

### **5. Add New Template Mapping:**

```python
# Add custom mapping
manager.add_form_id_mapping('new_form', 'HL0000099')

# Use new template
template = manager.get_template('new_form')
```

---

## 🔒 Security Features

### **1. Input Validation:**
- Validate API response structure
- Check required fields
- Verify data types

### **2. Security Logging:**
```python
# Every API call is logged
SecurityLogger.log_security_event(
    "TEMPLATE_API_SUCCESS",
    "system",
    {
        'form_id': 'HL0000050',
        'doc_name': 'Receipt-Bill',
        'attempt': 1
    }
)
```

### **3. Error Handling:**
- Timeout protection (30s default)
- Connection error handling
- JSON decode error handling
- Retry mechanism with exponential backoff

### **4. Security Headers:**
```python
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'ExtractForm-TemplateManager/1.0'
}
```

---

## 📊 Monitoring & Statistics

### **Available Metrics:**
```python
stats = manager.get_statistics()

# Metrics included:
{
    'api_calls': 10,           # Total API calls
    'cache_hits': 15,          # Cache hits
    'cache_misses': 10,        # Cache misses
    'api_errors': 0,           # API errors
    'fallback_uses': 0,        # Fallback uses
    'cache': {
        'total_cached': 6,     # Templates in cache
        'cached_forms': ['HL0000050', 'HL0000052', ...]
    }
}
```

### **Log Examples:**
```
2025-10-16 12:00:00 - INFO - Getting template: medical_receipt (formId: HL0000050)
2025-10-16 12:00:00 - INFO - Template loaded from cache: HL0000050
2025-10-16 12:00:01 - INFO - Fetching template from API: HL0000052 (attempt 1/3)
2025-10-16 12:00:02 - INFO - Template fetched successfully: HL0000052
```

---

## 🧪 Testing

### **Run Tests:**
```bash
# Test template API manager
python template_api_manager.py

# Test full integration
python test_template_api_integration.py
```

### **Test Coverage:**
1. ✅ Basic template fetching
2. ✅ Cache functionality
3. ✅ All templates retrieval
4. ✅ Fallback mechanism
5. ✅ Field extraction
6. ✅ Statistics monitoring

---

## 🔧 Troubleshooting

### **Problem: API Timeout**
```python
# Solution: Increase timeout
config['templates']['api']['timeout'] = 60  # 60 seconds
```

### **Problem: Cache Not Working**
```python
# Solution: Enable cache
config['templates']['cache_enabled'] = True
config['templates']['cache_ttl'] = 60
```

### **Problem: Template Not Found**
```python
# Solution 1: Check form_id_mapping
manager.add_form_id_mapping('my_form', 'HL0000099')

# Solution 2: Enable fallback
config['templates']['fallback_enabled'] = True
```

### **Problem: API Connection Error**
```python
# Solution: Check fallback files
# Ensure ./templates/medical_receipt_structure.json exists

# Verify API URL
config['templates']['api']['url']  # Should be correct
```

---

## 📈 Performance Optimization

### **1. Cache Tuning:**
```json
{
  "cache_enabled": true,
  "cache_ttl": 60  // Adjust based on update frequency
}
```

**Recommendations:**
- TTL = 60 min: Templates change rarely (Production)
- TTL = 30 min: Templates change occasionally (Staging)
- TTL = 5 min: Templates change frequently (Development)

### **2. API Optimization:**
```json
{
  "api": {
    "timeout": 30,      // Balance between wait time and reliability
    "max_retries": 3    // 3 retries = good balance
  }
}
```

### **3. Fallback Strategy:**
```json
{
  "fallback_enabled": true,  // Always enable for production
  "directory": "./templates"
}
```

---

## 🎯 Best Practices

### **1. Production Setup:**
```json
{
  "templates": {
    "api": {
      "enabled": true,
      "timeout": 30,
      "max_retries": 3
    },
    "cache_enabled": true,
    "cache_ttl": 60,
    "fallback_enabled": true
  }
}
```

### **2. Development Setup:**
```json
{
  "templates": {
    "api": {
      "enabled": true,
      "timeout": 10,
      "max_retries": 1
    },
    "cache_enabled": false,  // Disable for testing
    "fallback_enabled": true
  }
}
```

### **3. Code Best Practices:**
```python
# Always check if template exists
template = manager.get_template('medical_receipt')
if not template:
    logger.error("Template not found")
    return

# Use try-except
try:
    template = manager.get_template('medical_receipt')
except Exception as e:
    logger.error(f"Error: {e}")
    # Use fallback or default behavior
```

---

## 📝 Migration Guide

### **From Local Files to API:**

**Step 1: Update config.json**
```json
{
  "templates": {
    "api": {
      "url": "https://ocr.rg.in.th/uapi/api/KOConfiguration-GetFormId",
      "enabled": true
    }
  }
}
```

**Step 2: Replace TemplateManager with TemplateAPIManager**
```python
# Old code:
from template_manager import TemplateManager
manager = TemplateManager(config)

# New code:
from template_api_manager import TemplateAPIManager
manager = TemplateAPIManager(config)
```

**Step 3: Update code (minimal changes)**
```python
# API is same as before!
template = manager.get_template('medical_receipt')
```

**Step 4: Test thoroughly**
```bash
python test_template_api_integration.py
```

---

## 🔗 Form ID Reference

| Template Name | Form ID | Document Type |
|---------------|---------|---------------|
| medical_receipt | HL0000050 | Receipt-Bill |
| receipt | HL0000050 | Receipt-Bill |
| invoice | HL0000052 | Invoice |
| detail | HL0000053 | Detail |
| estimate | HL0000054 | Estimate Medical Expense |
| statement | HL0000055 | Statement from Hospital |
| endorsement | NO00C0000 | Beneficiary Endorsement |

**ต้องการเพิ่ม Form ID ใหม่:**
1. Update `config.json` → `form_id_mapping`
2. หรือใช้ `manager.add_form_id_mapping('name', 'FORM_ID')`

---

## ✅ Checklist

### **Implementation:**
- ✅ Created `template_api_manager.py`
- ✅ Updated `config.json` with API settings
- ✅ Created test suite `test_template_api_integration.py`
- ✅ Added security validation
- ✅ Implemented caching mechanism
- ✅ Added fallback to local files
- ✅ Created documentation

### **Features:**
- ✅ Dynamic template loading from API
- ✅ Cache with configurable TTL
- ✅ Automatic fallback
- ✅ Security logging
- ✅ Statistics tracking
- ✅ Error handling
- ✅ Retry mechanism

---

## 📞 Support

### **Common Issues:**
1. **API Timeout:** Increase timeout in config
2. **Cache Issues:** Clear cache or disable caching
3. **Template Not Found:** Check form_id_mapping
4. **Connection Error:** Enable fallback mode

### **Documentation:**
- `TEMPLATE_API_INTEGRATION_GUIDE.md` - This file
- `template_api_manager.py` - Source code with comments
- `config.json` - Configuration reference

---

**สถานะ:** ✅ **READY FOR PRODUCTION**  
**วันที่:** 16 ตุลาคม 2568  
**Version:** 1.0.0

---

*ระบบสามารถดึง template จาก API แบบ dynamic พร้อม cache, security และ fallback ครบถ้วน!* 🚀

