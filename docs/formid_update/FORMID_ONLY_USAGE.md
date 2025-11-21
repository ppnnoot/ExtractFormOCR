# การใช้งานด้วย Form ID เท่านั้น

## 🎯 สิ่งที่เปลี่ยนแปลง

ระบบได้รับการปรับปรุงให้**รองรับแค่ Form ID** เพื่อ:
- ✅ **ลดเงื่อนไข** - ไม่ต้อง map ชื่อเป็น Form ID
- ✅ **เพิ่มความเร็ว** - ประมวลผลตรงไปตรงมา
- ✅ **ลดความซับซ้อน** - ใช้ ID เดียวทั่วทั้งระบบ

## 📋 Form IDs ที่รองรับ

| Form ID | ประเภทเอกสาร |
|---------|--------------|
| **HL0000050** | Receipt-Bill (ใบเสร็จรับเงิน/ใบแจ้งหนี้) |
| **HL0000052** | Invoice (ใบแจ้งหนี้) |
| **HL0000053** | Detail (ใบแจ้งรายละเอียดค่ารักษาพยาบาล) |
| **HL0000054** | Estimate (ใบประเมินค่าใช้จ่าย/GOP) |
| **HL0000055** | Statement (สรุปค่ารักษา) |

## 💻 วิธีใช้งาน

### 1. Extract จาก OCR Text

```python
import requests

response = requests.post(
    "http://localhost:8888/extract/text",
    json={
        "ocr_texts": ["ใบเสร็จรับเงิน", "โรงพยาบาล ABC", "ยอดรวม 5,000 บาท"],
        "form_id": "HL0000050"  # ระบุ Form ID โดยตรง
    }
)

print(response.json())
```

### 2. Extract จากรูปภาพ

```python
import requests

with open("receipt.jpg", "rb") as f:
    response = requests.post(
        "http://localhost:8888/extract/image",
        files={"file": f},
        params={"form_id": "HL0000052"}  # ระบุ Form ID
    )

print(response.json())
```

### 3. ดูรายการ Form IDs ทั้งหมด

```bash
curl http://localhost:8888/templates/form-ids
```

**Response:**
```json
{
  "success": true,
  "form_ids": [
    {
      "form_id": "HL0000050",
      "document_type": "Receipt-Bill",
      "document_type_thai": "ใบเสร็จรับเงิน",
      "description": "ใบเสร็จรับเงิน/ใบแจ้งหนี้"
    }
  ],
  "total": 5,
  "note": "Use 'form_id' directly in API requests"
}
```

## 🔧 API Endpoints

### POST `/extract/text`
Extract จาก OCR text ด้วย Form ID

**Request:**
```json
{
  "ocr_texts": ["text1", "text2", "..."],
  "form_id": "HL0000050"
}
```

### POST `/extract/image`
Extract จากรูปภาพด้วย Form ID

**Parameters:**
- `file`: รูปภาพ (multipart/form-data)
- `form_id`: Form ID (query parameter)

### GET `/templates/form-ids`
ดูรายการ Form IDs ทั้งหมดจาก API

**Response:**
```json
{
  "success": true,
  "form_ids": [...],
  "total": 5
}
```

## ⚡ ตัวอย่างการใช้งานจริง

### Dynamic Form ID จาก Classification
```python
# 1. Classify เอกสาร
classification = classify_document(ocr_texts)
form_id = classification['form_id']  # เช่น "HL0000053"

# 2. Extract ด้วย Form ID ที่ได้
result = requests.post(
    "http://localhost:8888/extract/text",
    json={
        "ocr_texts": ocr_texts,
        "form_id": form_id
    }
)
```

### Batch Processing
```python
documents = [
    {"texts": [...], "form_id": "HL0000050"},
    {"texts": [...], "form_id": "HL0000052"},
    {"texts": [...], "form_id": "HL0000053"},
]

for doc in documents:
    response = requests.post(
        "http://localhost:8888/extract/text",
        json={
            "ocr_texts": doc["texts"],
            "form_id": doc["form_id"]
        }
    )
    print(f"Processed {doc['form_id']}: {response.status_code}")
```

## 📦 ข้อมูลที่ส่งกลับ

Response จะมี `formId` และ `docName` จาก Template API:

```json
{
  "success": true,
  "data": {
    "formId": "HL0000050",
    "docName": "Receipt-Bill",
    "documentCode": "CM0000095",
    "receiptInfo": {...},
    "patientInfo": {...},
    "billingItems": [...]
  }
}
```

## ⚠️ หมายเหตุสำคัญ

1. **Form ID ต้องถูกต้อง** - ตรวจสอบจาก `/templates/form-ids` ก่อนใช้งาน
2. **Case Sensitive** - Form ID เป็นตัวพิมพ์ใหญ่ (HL0000050 ไม่ใช่ hl0000050)
3. **Default Form ID** - ถ้าไม่ระบุจะใช้ `HL0000050` (Receipt-Bill)

## 🚀 Quick Test

```bash
# ทดสอบ API
curl -X POST "http://localhost:8888/extract/text" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": ["ใบเสร็จรับเงิน", "โรงพยาบาล ABC"],
    "form_id": "HL0000050"
  }'
```

## 📈 ประโยชน์ที่ได้รับ

- ⚡ **เร็วขึ้น** - ไม่ต้องแปลงชื่อเป็น Form ID
- 🎯 **แม่นยำขึ้น** - ใช้ ID จากระบบโดยตรง
- 🔧 **ง่ายขึ้น** - API ชัดเจน ใช้งานง่าย
- 📦 **ลดโค้ด** - เอา mapping layer ออก

---

**Version:** 2.1.0  
**Updated:** 19 ตุลาคม 2567  
**Status:** ✅ พร้อมใช้งาน

