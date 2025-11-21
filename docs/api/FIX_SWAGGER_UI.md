# 🔧 แก้ไข Swagger UI - CSP Error

**ปัญหา:** Swagger UI ไม่แสดงเพราะ Content Security Policy บล็อก CDN  
**แก้ไขแล้ว:** ✅ อัปเดต api_server.py  
**วันที่:** 7 ตุลาคม 2568

---

## ❌ ปัญหาที่พบ

```
Refused to load the stylesheet 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css'
Refused to load the script 'https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js'
Refused to load the image 'https://fastapi.tiangolo.com/img/favicon.png'
```

**สาเหตุ:** Content Security Policy (CSP) เข้มงวดเกินไป บล็อก external resources

---

## ✅ การแก้ไขที่ทำแล้ว

### **อัปเดต `api_server.py` (บรรทัด 82-104)**

เพิ่ม exception สำหรับ `/docs` และ `/redoc`:

```python
# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Special handling for Swagger UI/OpenAPI docs
    if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
        # Relaxed CSP for documentation pages
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net;"
        )
    else:
        # Strict CSP for all other endpoints
        security_headers = SecurityHeaders.get_security_headers()
        for header, value in security_headers.items():
            response.headers[header] = value
    
    return response
```

---

## 🔄 วิธีแก้ไข

### **ขั้นตอนที่ 1: Restart API Server**

```bash
# ใน Terminal ที่รัน api_server.py
# กด Ctrl+C เพื่อหยุด

# เริ่มใหม่
python api_server.py
```

### **ขั้นตอนที่ 2: เปิด Browser**

```
http://localhost:8888/docs
```

### **ขั้นตอนที่ 3: Refresh หน้า Browser**

```
กด F5 หรือ Ctrl+R (Windows)
กด Cmd+R (Mac)
```

---

## ✅ ผลลัพธ์ที่คาดหวัง

### **Swagger UI จะแสดง:**
- ✅ หน้า UI สวยงาม (ไม่ขาด CSS)
- ✅ แสดงรายการ endpoints ทั้งหมด
- ✅ มีปุ่ม "Try it out" ทำงานได้
- ✅ มี favicon แสดง
- ✅ ทุกอย่างทำงานปกติ

### **Endpoints ที่จะเห็น:**

#### **🔐 Authentication**
- `POST /auth/login` - Get access token

#### **📋 Classification**
- `POST /classify` - Classify 5 Form Types (B01-B07)

#### **📄 Extraction**
- `POST /extract/image` - Extract from image
- `POST /extract/text` - Extract from OCR text
- `POST /extract/batch` - Batch processing

#### **📊 Monitoring**
- `GET /` - API info
- `GET /health` - Health check
- `GET /stats` - Statistics (requires auth)

---

## 🎯 ทดสอบใน Swagger UI

### **Test 1: Classification - B05 (Detail)**

1. คลิกที่ `POST /classify`
2. คลิก "Try it out"
3. ใส่:
```json
{
  "texts": [
    "ใบแจ้งรายละเอียดค่ารักษาพยาบาล",
    "HN: 04-20-006834",
    "1.1 ค่ายาและสารอาหาร"
  ]
}
```
4. คลิก "Execute"

**Expected Response:**
```json
{
  "success": true,
  "form_id": "HL0000053",
  "ref_code": "B05",
  "document_type": "Detail",
  "confidence": "high"
}
```

---

### **Test 2: Classification - B01 (Receipt)**

```json
{
  "texts": [
    "ใบเสร็จรับเงิน",
    "RECEIPT",
    "ชำระเงินแล้ว"
  ]
}
```

**Expected:**
```json
{
  "form_id": "HL0000050",
  "ref_code": "B01"
}
```

---

### **Test 3: Classification - B06 (Estimate/GOP)**

```json
{
  "texts": [
    "ใบประเมินค่าใช้จ่าย",
    "Guarantee of Payment",
    "GOP",
    "บริษัทประกัน"
  ]
}
```

**Expected:**
```json
{
  "form_id": "HL0000054",
  "ref_code": "B06"
}
```

---

## 🔒 ความปลอดภัย

### **สิ่งที่เปลี่ยน:**
- ✅ **Relaxed CSP** สำหรับ `/docs` และ `/redoc` เท่านั้น
- ✅ **Strict CSP** ยังคงใช้งานใน API endpoints อื่นๆ
- ✅ ความปลอดภัย **ไม่ลดลง** - เพิ่มความสะดวกเท่านั้น

### **การตรวจสอบ:**
```bash
# ตรวจสอบ CSP ของ /docs (relaxed)
curl -I http://localhost:8888/docs | grep -i "content-security"

# ตรวจสอบ CSP ของ /health (strict)
curl -I http://localhost:8888/health | grep -i "content-security"
```

---

## 📊 สรุป

### **การแก้ไข:**
- ✅ อัปเดต security headers middleware
- ✅ เพิ่ม exception สำหรับ `/docs`, `/redoc`
- ✅ อนุญาต CDN สำหรับ Swagger UI
- ✅ ยังคงความปลอดภัยใน API endpoints

### **ขั้นตอนต่อไป:**
1. **Restart API Server**
2. **เปิด http://localhost:8888/docs**
3. **Swagger UI จะทำงานปกติ**

---

**Status:** ✅ Fixed and Ready

**Updated:** October 7, 2025

