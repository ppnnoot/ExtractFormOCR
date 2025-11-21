# Migration Guide: จาก Template Name เป็น Form ID

## 📋 ภาพรวม

ระบบได้รับการอัปเดตให้ใช้แค่ **Form ID โดยตรง** แทนการใช้ชื่อ template

## 🔄 การเปลี่ยนแปลง

### ก่อน (ใช้ชื่อ template)
```python
{
  "ocr_texts": ["..."],
  "template": "medical_receipt"  # ❌ ไม่รองรับแล้ว
}
```

### หลัง (ใช้ Form ID)
```python
{
  "ocr_texts": ["..."],
  "form_id": "HL0000050"  # ✅ ใช้ Form ID โดยตรง
}
```

## 🗺️ Mapping Table

ถ้าคุณใช้ชื่อ template เดิม ให้เปลี่ยนเป็น Form ID ตามตารางนี้:

| ชื่อเดิม (Template) | Form ID ใหม่ | ประเภทเอกสาร |
|---------------------|--------------|--------------|
| `medical_receipt` | `HL0000050` | Receipt-Bill |
| `receipt` | `HL0000050` | Receipt-Bill |
| `invoice` | `HL0000052` | Invoice |
| `detail` | `HL0000053` | Detail |
| `estimate` | `HL0000054` | Estimate |
| `statement` | `HL0000055` | Statement |

## 🔧 วิธี Migrate โค้ด

### 1. Extract Text API

**ก่อน:**
```python
response = requests.post(
    "http://localhost:8888/extract/text",
    json={
        "ocr_texts": ["..."],
        "template": "invoice"  # ❌
    }
)
```

**หลัง:**
```python
response = requests.post(
    "http://localhost:8888/extract/text",
    json={
        "ocr_texts": ["..."],
        "form_id": "HL0000052"  # ✅
    }
)
```

### 2. Extract Image API

**ก่อน:**
```python
response = requests.post(
    "http://localhost:8888/extract/image",
    files={"file": f},
    params={"template": "detail"}  # ❌
)
```

**หลัง:**
```python
response = requests.post(
    "http://localhost:8888/extract/image",
    files={"file": f},
    params={"form_id": "HL0000053"}  # ✅
)
```

### 3. ใช้ตัวแปร

**ก่อน:**
```python
template_name = "estimate"  # ❌

response = requests.post(url, json={
    "ocr_texts": texts,
    "template": template_name
})
```

**หลัง:**
```python
form_id = "HL0000054"  # ✅

response = requests.post(url, json={
    "ocr_texts": texts,
    "form_id": form_id
})
```

### 4. Dynamic Selection

**ก่อน:**
```python
# Mapping ในโค้ดของคุณ
template_map = {
    "receipt_type": "medical_receipt",
    "invoice_type": "invoice"
}
selected_template = template_map[doc_type]  # ❌
```

**หลัง:**
```python
# ใช้ Form ID โดยตรง
form_id_map = {
    "receipt_type": "HL0000050",
    "invoice_type": "HL0000052"
}
selected_form_id = form_id_map[doc_type]  # ✅
```

## 📝 Checklist

- [ ] เปลี่ยน parameter `template` เป็น `form_id`
- [ ] แปลงชื่อ template เป็น Form ID ตามตาราง
- [ ] อัปเดตตัวแปรและ configuration
- [ ] เปลี่ยน endpoint `/templates/mapping` เป็น `/templates/form-ids`
- [ ] ทดสอบ API ทั้งหมดให้ทำงานถูกต้อง

## 🧪 การทดสอบ

### 1. ทดสอบ API ด้วย cURL
```bash
curl -X POST "http://localhost:8888/extract/text" \
  -H "Content-Type: application/json" \
  -d '{
    "ocr_texts": ["test"],
    "form_id": "HL0000050"
  }'
```

### 2. ทดสอบด้วย Python
```python
import requests

# ทดสอบทุก Form ID
form_ids = ["HL0000050", "HL0000052", "HL0000053", "HL0000054", "HL0000055"]

for form_id in form_ids:
    response = requests.post(
        "http://localhost:8888/extract/text",
        json={
            "ocr_texts": ["test"],
            "form_id": form_id
        }
    )
    print(f"{form_id}: {response.status_code}")
```

## ⚙️ การอัปเดต Configuration

### ถ้าคุณมี Config File
```python
# ก่อน
config = {
    "default_template": "medical_receipt"  # ❌
}

# หลัง
config = {
    "default_form_id": "HL0000050"  # ✅
}
```

### ถ้าคุณมี Environment Variables
```bash
# ก่อน
export DEFAULT_TEMPLATE=medical_receipt  # ❌

# หลัง
export DEFAULT_FORM_ID=HL0000050  # ✅
```

## 🔍 การตรวจสอบหาโค้ดที่ต้องแก้

### ค้นหาใน Code
```bash
# ค้นหา "template" ที่อาจต้องแก้
grep -r "template" --include="*.py" .

# ค้นหา field "template" ใน JSON/dict
grep -r '"template":' --include="*.py" .
```

### Pattern ที่ต้องแก้
- `"template": "medical_receipt"` → `"form_id": "HL0000050"`
- `template=xxx` → `form_id=xxx`
- `get_template(name)` → `get_template(form_id)`

## 🚨 ปัญหาที่อาจพบ

### 1. ส่ง template แทน form_id
```python
# ❌ จะได้ error
{"ocr_texts": [...], "template": "invoice"}

# Error: Field 'form_id' is required
```

**วิธีแก้:** เปลี่ยนเป็น `"form_id": "HL0000052"`

### 2. ใช้ชื่อแทน Form ID
```python
# ❌ ส่งชื่อแทน Form ID
{"form_id": "invoice"}

# จะไม่เจอ template
```

**วิธีแก้:** ใช้ Form ID ที่ถูกต้อง: `"form_id": "HL0000052"`

### 3. Case Sensitivity
```python
# ❌ Form ID ต้องเป็นตัวพิมพ์ใหญ่
{"form_id": "hl0000050"}
```

**วิธีแก้:** `"form_id": "HL0000050"` (ตัวพิมพ์ใหญ่)

## 💡 Tips

1. **ใช้ constants** - สร้าง constants file สำหรับ Form IDs
   ```python
   # constants.py
   FORM_ID_RECEIPT = "HL0000050"
   FORM_ID_INVOICE = "HL0000052"
   FORM_ID_DETAIL = "HL0000053"
   FORM_ID_ESTIMATE = "HL0000054"
   FORM_ID_STATEMENT = "HL0000055"
   ```

2. **Validate Form ID** - ตรวจสอบก่อนส่ง request
   ```python
   VALID_FORM_IDS = ["HL0000050", "HL0000052", "HL0000053", "HL0000054", "HL0000055"]
   
   if form_id not in VALID_FORM_IDS:
       raise ValueError(f"Invalid Form ID: {form_id}")
   ```

3. **ดึงรายการ Form IDs จาก API** - ไม่ต้อง hardcode
   ```python
   response = requests.get("http://localhost:8888/templates/form-ids")
   available_form_ids = [f['form_id'] for f in response.json()['form_ids']]
   ```

## 📞 ต้องการความช่วยเหลือ?

- **ดูเอกสาร:** `FORMID_ONLY_USAGE.md`
- **ดูตัวอย่าง:** ตรวจสอบ API Documentation ที่ http://localhost:8888/docs
- **ดู Form IDs:** `curl http://localhost:8888/templates/form-ids`

---

**เวอร์ชัน:** 2.1.0  
**วันที่:** 19 ตุลาคม 2567

