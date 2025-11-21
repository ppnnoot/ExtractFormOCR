# 🔄 Document Code & Type from Template API

**วันที่:** 16 ตุลาคม 2568  
**การเปลี่ยนแปลง:** ดึง document_code และ document_type จาก Template API  
**สถานะ:** ✅ **IMPLEMENTED**

---

## 🎯 สรุปการเปลี่ยนแปลง

### **ก่อน (Hard-coded):**
```json
{
  "documents": [
    {
      "document_code": "CM1760593672479",  // ❌ Generated from timestamp
      "document_type": "Detail",           // ❌ Hard-coded
      ...
    }
  ]
}
```

### **หลัง (From API):**
```json
{
  "documents": [
    {
      "document_code": "HL0000050",      // ✅ From API (formId)
      "document_type": "Receipt-Bill",   // ✅ From API (docName)
      ...
    }
  ]
}
```

---

## 📊 Mapping

### **Template API Response:**
```json
{
  "formId": "HL0000050",
  "docName": "Receipt-Bill",
  "docThaiName": "ใบเสร็จรับเงิน/ใบแจ้งหนี้",
  ...
}
```

### **JSON Output Mapping:**
```
formId   → document_code   (e.g., "HL0000050")
docName  → document_type   (e.g., "Receipt-Bill")
```

---

## 🔧 การแก้ไข

### **1. เพิ่ม template_config Parameter:**

**ไฟล์:** `ai_simple_extraction.py` → `format_to_medical_receipt_json()`

```python
# เดิม
def format_to_medical_receipt_json(
    simple_data: Dict[str, Any], 
    metadata: Dict[str, Any] = None,
    transaction_no: str = None,
    document_code: str = None
) -> Dict[str, Any]:

# ใหม่
def format_to_medical_receipt_json(
    simple_data: Dict[str, Any], 
    metadata: Dict[str, Any] = None,
    transaction_no: str = None,
    document_code: str = None,
    template_config: Dict[str, Any] = None  # NEW!
) -> Dict[str, Any]:
```

---

### **2. ดึง document_code จาก Template API (formId):**

```python
# Get document_code from template API (formId) or generate if not provided
if not document_code:
    if template_config and 'form_id' in template_config:
        document_code = template_config['form_id']  # Use formId from API
        logger.info(f"Using document_code from template API: {document_code}")
    else:
        document_code = f"CM{int(time.time() * 1000)}"
        logger.warning(f"Template API not available, using generated document_code: {document_code}")
```

**Priority:**
1. ถ้ามี template_config → ใช้ `formId` จาก API ✅
2. ถ้าไม่มี → สร้างจาก timestamp (fallback)

---

### **3. ดึง document_type จาก Template API (docName):**

```python
# Get document_type from template API (docName) or use default
if template_config and 'document_type' in template_config:
    document_type = template_config['document_type']  # Use docName from API
    logger.info(f"Using document_type from template API: {document_type}")
else:
    document_type = "Detail"  # Default fallback
    logger.warning(f"Template API not available, using default document_type: {document_type}")
```

**Priority:**
1. ถ้ามี template_config → ใช้ `docName` จาก API ✅
2. ถ้าไม่มี → ใช้ "Detail" (fallback)

---

### **4. อัพเดต JSON Output:**

```python
# เดิม
{
    "document_code": document_code,
    "document_type": "Detail",  // ❌ Hard-coded
    ...
}

# ใหม่
{
    "document_code": document_code,  # From API formId
    "document_type": document_type,  # From API docName ✅
    ...
}
```

---

### **5. อัพเดตการเรียกใช้:**

```python
# ใน process_document()

# เดิม
formatted_json = self.json_formatter.format_to_medical_receipt_json(
    simple_data, 
    metadata
)

# ใหม่
formatted_json = self.json_formatter.format_to_medical_receipt_json(
    simple_data, 
    metadata,
    template_config=template_config  # NEW: Pass template config from API
)
```

---

## 📊 ตัวอย่าง

### **Example 1: HL0000050 (Receipt-Bill)**

**Template API Response:**
```json
{
  "form_id": "HL0000050",
  "document_type": "Receipt-Bill",
  "document_type_thai": "ใบเสร็จรับเงิน/ใบแจ้งหนี้"
}
```

**JSON Output:**
```json
{
  "transaction_no": "TX1760593672479",
  "documents": [
    {
      "document_code": "HL0000050",     // ✅ From formId
      "document_type": "Receipt-Bill",  // ✅ From docName
      "need_correction": false,
      "total_page": "1",
      "page": "1",
      "document_info": [...]
    }
  ]
}
```

---

### **Example 2: HL0000052 (Invoice)**

**Template API Response:**
```json
{
  "form_id": "HL0000052",
  "document_type": "Invoice",
  "document_type_thai": "Invoice"
}
```

**JSON Output:**
```json
{
  "documents": [
    {
      "document_code": "HL0000052",  // ✅ From formId
      "document_type": "Invoice",    // ✅ From docName
      ...
    }
  ]
}
```

---

### **Example 3: HL0000054 (Estimate)**

**Template API Response:**
```json
{
  "form_id": "HL0000054",
  "document_type": "Estimate Medical Expense report, GOP, guarantee email",
  "document_type_thai": "ใบประเมินค่าใช้จ่าย-ใบการันตีความคุ้มครอง-เมล์แจ้งผลการพิจารณา"
}
```

**JSON Output:**
```json
{
  "documents": [
    {
      "document_code": "HL0000054",  // ✅ From formId
      "document_type": "Estimate Medical Expense report, GOP, guarantee email",  // ✅ Full name from API
      ...
    }
  ]
}
```

---

## 🔍 Logging

### **เมื่อดึงจาก API สำเร็จ:**
```
INFO - Using document_code from template API: HL0000050
INFO - Using document_type from template API: Receipt-Bill
```

### **เมื่อ API ไม่พร้อม (Fallback):**
```
WARNING - Template API not available, using generated document_code: CM1760593672479
WARNING - Template API not available, using default document_type: Detail
```

---

## ✅ Benefits

### **1. Consistency:**
- ✅ document_code และ document_type ตรงกับ Template API
- ✅ ไม่มีการ hard-code values
- ✅ Single source of truth

### **2. Flexibility:**
- ✅ เปลี่ยน template ที่ API → JSON output จะเปลี่ยนตาม
- ✅ เพิ่มฟอร์มใหม่ที่ API → รองรับทันที

### **3. Traceability:**
- ✅ รู้ว่า document มาจาก template ไหน (formId)
- ✅ มี logging ชัดเจน
- ✅ Fallback ทำงานถ้า API down

---

## 📋 Template Mappings

| Template | formId | docName |
|----------|--------|---------|
| medical_receipt | HL0000050 | Receipt-Bill |
| invoice | HL0000052 | Invoice |
| detail | HL0000053 | detail |
| estimate | HL0000054 | Estimate Medical Expense report |
| statement | HL0000055 | Statement from Hospital |
| endorsement | NO00C0000 | Beneficiary endorsement |

---

## 🧪 Testing

### **Test Case 1: Normal Flow (API Available)**

```bash
curl -X POST http://localhost:8888/extract/text \
  -H 'Content-Type: application/json' \
  -d '{
    "ocr_texts": ["..."],
    "template": "medical_receipt"
  }'
```

**Expected Response:**
```json
{
  "documents": [
    {
      "document_code": "HL0000050",     // ✅ From API
      "document_type": "Receipt-Bill",  // ✅ From API
      ...
    }
  ]
}
```

**Expected Logs:**
```
INFO - Template loaded: Receipt-Bill (Form ID: HL0000050) in 0.005s
INFO - Using document_code from template API: HL0000050
INFO - Using document_type from template API: Receipt-Bill
```

---

### **Test Case 2: Fallback (API Down)**

**Scenario:** Template API ไม่พร้อม

**Expected Response:**
```json
{
  "documents": [
    {
      "document_code": "CM1760593672479",  // ⚠️ Generated
      "document_type": "Detail",           // ⚠️ Default
      ...
    }
  ]
}
```

**Expected Logs:**
```
WARNING - Template 'medical_receipt' not found, using default
WARNING - Template API not available, using generated document_code: CM1760593672479
WARNING - Template API not available, using default document_type: Detail
```

---

## 🎯 Summary

### **Changes Made:**
1. ✅ เพิ่ม `template_config` parameter ใน `format_to_medical_receipt_json()`
2. ✅ ดึง `document_code` จาก `template_config['form_id']` (formId)
3. ✅ ดึง `document_type` จาก `template_config['document_type']` (docName)
4. ✅ อัพเดตการเรียกใช้ให้ส่ง `template_config` ไปด้วย
5. ✅ เพิ่ม logging สำหรับ debugging
6. ✅ มี fallback ถ้า API ไม่พร้อม

### **Files Modified:**
```
ai_simple_extraction.py
├── format_to_medical_receipt_json()  ✅ Add template_config param
├──   - Get document_code from formId   ✅ 
├──   - Get document_type from docName  ✅
└── process_document()                ✅ Pass template_config

+ DOCUMENT_CODE_TYPE_FROM_API.md     ✅ This document
```

### **Impact:**
- 🎯 **Consistency:** ข้อมูลตรงกับ Template API
- 🔄 **Dynamic:** เปลี่ยนที่ API → JSON output เปลี่ยนตาม
- 🛡️ **Reliable:** มี fallback ถ้า API down
- 📊 **Traceable:** มี logging ครบถ้วน

---

**สถานะ:** ✅ **IMPLEMENTED & READY TO USE**

---

**Created:** 16 ตุลาคม 2568  
**Modified:** ai_simple_extraction.py  
**Lines Changed:** +35 lines  
**Impact:** HIGH (affects all JSON outputs)

---

*Now document_code and document_type come from the Template API - Single source of truth!* 🎯✨

