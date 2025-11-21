# ✅ Implementation Checklist & Workflow

## 🎯 Complete Project Checklist

### Phase 1: Foundation (Day 1-2)
- [ ] Setup project structure
- [ ] Install dependencies
- [ ] Configure OneOCR integration
- [ ] Test OCR basic functionality
- [ ] Create sample test images

### Phase 2: Core Components (Day 3-5)
- [ ] Implement OCR Adapter (multi-engine support)
- [ ] Create Spatial Analyzer
- [ ] Test spatial relationships
- [ ] Implement basic extraction logic
- [ ] Create visualization tools

### Phase 3: Template System (Day 6-7)
- [ ] Design template JSON format
- [ ] Implement Template Manager
- [ ] Create default templates (invoice, receipt, ID card)
- [ ] Implement template-based extractor
- [ ] Test with sample documents

### Phase 4: AI Integration (Day 8-10)
- [ ] Test AI API connection
- [ ] Design AI prompt structure
- [ ] Implement AI Extraction Engine
- [ ] Create prompt templates
- [ ] Test extraction accuracy
- [ ] Implement response parsing

### Phase 5: Hybrid System (Day 11-12)
- [ ] Implement quality assessment
- [ ] Create fallback mechanism
- [ ] Test hybrid mode
- [ ] Optimize threshold settings
- [ ] Add statistics tracking

### Phase 6: Integration & Testing (Day 13-14)
- [ ] Integrate all components
- [ ] Create main pipeline
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Performance testing
- [ ] Bug fixes

### Phase 7: Production Ready (Day 15+)
- [ ] Add error handling
- [ ] Implement logging
- [ ] Create configuration system
- [ ] Add CLI interface
- [ ] Write documentation
- [ ] Create examples
- [ ] Deploy

---

## 🔄 Recommended Conversation Flow with AI

### 📝 Session 1: Project Setup

**You:**
```
ฉันต้องการสร้างระบบ OCR Pipeline สำหรับองค์กร โดยมี requirements:

1. ใช้ OneOCR (Windows DLL) - มีไฟล์อยู่แล้ว
2. วิเคราะห์ spatial layout (x, y, bbox)
3. ส่งให้ AI วิเคราะห์และ extract
4. Export เป็น JSON ตาม template

AI API: http://10.5.19.205:8080/v1/chat/completions
Model: openai/gpt-oss-20b

ช่วยออกแบบ system architecture และ file structure
```

**AI Response:** จะให้ architecture diagram และ file structure

**Follow-up:**
```
เริ่มจาก OCR Adapter ก่อน - เขียน class ที่ wrap OneOCR DLL 
โดยรองรับ:
- Multiple OCR engines (OneOCR, EasyOCR, PaddleOCR)
- Unified output format
- Error handling และ fallback

[วาง example code ของ OneOCR ที่มีอยู่]
```

---

### 📝 Session 2: Spatial Analysis

**You:**
```
ต่อไป สร้าง Spatial Analyzer ที่วิเคราะห์:

Input:
```json
[
  {"text": "Invoice No:", "bbox": [[50,120],...], "confidence": 0.9},
  {"text": "INV-001", "bbox": [[210,120],...], "confidence": 0.92}
]
```

Features:
1. จัดกลุ่มเป็น lines (y coordinate)
2. ตรวจจับ columns (x coordinate)
3. find_text_right_of(label)
4. find_text_below(label)
5. detect_table_structure()

Parameters:
- line_threshold: 20px
- column_threshold: 50px
```

**Follow-up:**
```
เพิ่ม visualization - วาด bounding boxes บนรูปภาพ
แสดง relationships ด้วยสีต่างๆ
```

---

### 📝 Session 3: AI Integration

**You:**
```
สร้าง AI Extraction Engine:

API Spec:
```json
{
  "endpoint": "http://10.5.19.205:8080/v1/chat/completions",
  "body": {
    "model": "openai/gpt-oss-20b",
    "messages": [...],
    "temperature": 0.1,
    "max_tokens": 2000
  }
}
```

ต้องการ:
1. สร้าง prompt ที่ส่ง OCR results + spatial info
2. กำหนด fields ที่ต้องการ extract
3. Parse JSON response
4. Quality assessment
5. Error handling
```

**Follow-up:**
```
ปรับ prompt ให้แม่นยำขึ้น - เพิ่มตัวอย่าง
และคำแนะนำเกี่ยวกับ spatial relationships
```

---

### 📝 Session 4: Template System

**You:**
```
สร้าง Template System:

Template format:
```json
{
  "fields": {
    "invoice_number": {
      "method": "spatial_right",
      "config": {"label": "Invoice No"},
      "required": true
    }
  },
  "output_structure": {
    "invoice": {"number": "${invoice_number}"}
  }
}
```

Extraction methods:
- spatial_right, spatial_below
- pattern (regex)
- position (x, y)
- table

Post-processing:
- trim, uppercase, extract_numbers, etc.
```

---

### 📝 Session 5: Integration

**You:**
```
รวมทุก component เป็น Complete Pipeline:

Flow:
OCR → Spatial → AI/Rule Extraction → JSON Output

Modes:
- ai: ใช้ AI เท่านั้น
- rule: ใช้ Rule-based เท่านั้น
- hybrid: AI first, fallback to rule

Features:
- Configuration management
- Batch processing
- Statistics
- CLI interface
```

---

## 🎬 Example Complete Conversation

### Starting Fresh:

**You:**
```
ฉันต้องการสร้าง AI-Powered OCR Pipeline ที่:

1. ใช้ OneOCR (Windows) สำหรับ OCR
2. วิเคราะห์ spatial layout (x, y, bounding boxes)
3. ส่งข้อมูลให้ AI API วิเคราะห์และ extract ข้อมูล
4. Export เป็น JSON ตาม template ที่กำหนด
5. มี fallback เป็น rule-based ถ้า AI ล้มเหลว

AI API: http://10.5.19.205:8080/v1/chat/completions
Model: openai/gpt-oss-20b

เอกสารที่ต้องการประมวลผล:
- ใบแจ้งหนี้ (Invoice)
- ใบเสร็จ (Receipt)
- บัตรประชาชน (ID Card)

ช่วยเริ่มจาก high-level architecture ก่อน
แล้วค่อยเขียนโค้ดแต่ละส่วน
```

**Expected AI Response:**
- System architecture diagram
- Component breakdown
- Data flow
- Tech stack recommendations

**Your Next Prompt:**
```
ดีมาก! เริ่มจาก OCR Adapter ก่อน

ฉันมี OneOCR code อยู่แล้ว:
[วางโค้ด]

ช่วย:
1. Refactor เป็น class structure
2. เพิ่ม support สำหรับ EasyOCR, PaddleOCR
3. Unified output format
4. Auto-fallback mechanism
```

**Continue iterating...**

---

## 💡 Tips for Effective Prompting

### ✅ DO:

1. **Start High-Level:**
   ```
   "ช่วยออกแบบ architecture ก่อน"
   ```

2. **Provide Context:**
   ```
   "ระบบนี้จะใช้ในองค์กรที่ประมวลผล 1000+ documents/day"
   ```

3. **Give Examples:**
   ```
   "ตัวอย่าง OCR output:"
   [วางตัวอย่าง]
   ```

4. **Ask for Alternatives:**
   ```
   "มีวิธีอื่นที่ดีกว่าไหม?"
   ```

5. **Request Tests:**
   ```
   "เขียน unit tests ด้วย"
   ```

### ❌ DON'T:

1. **Don't Ask Everything at Once:**
   ❌ "เขียนทั้งระบบให้หน่อย"
   ✅ "เริ่มจาก OCR Adapter ก่อน"

2. **Don't Be Vague:**
   ❌ "ทำให้ดีขึ้น"
   ✅ "เพิ่ม error handling และ retry logic"

3. **Don't Skip Context:**
   ❌ "เขียน extraction function"
   ✅ "เขียน extraction function ที่รับ OCR results และ template, คืนค่าเป็น dict"

---

## 📊 Quality Checklist

### Before Asking AI:
- [ ] รู้ requirements ชัดเจน
- [ ] มี example data/code
- [ ] เตรียมคำถาม follow-up

### After Getting Code:
- [ ] อ่านโค้ดและเข้าใจ
- [ ] Test functionality
- [ ] ถามเพิ่มเติมถ้าไม่ชัด
- [ ] Request improvements

### Before Moving On:
- [ ] โค้ดทำงานได้
- [ ] มี error handling
- [ ] มี documentation
- [ ] มี tests (ถ้าจำเป็น)

---

## 🔧 Debugging Prompts

### When Code Doesn't Work:

```
โค้ดนี้ error:
[วาง error message]

จาก code:
[วางโค้ดบริเวณที่ error]

ช่วย debug และแก้ไข
```

### When Need Optimization:

```
โค้ดนี้ช้า:
[วางโค้ด]

ประมวลผล 100 documents ใช้เวลา 5 นาที
ช่วย optimize
```

### When Need More Features:

```
เพิ่ม feature:
[อธิบาย feature]

ใน class นี้:
[วางโค้ด class]
```

---

## 🎓 Learning Path

### Beginner:
1. เริ่มจาก basic OCR integration
2. ทำความเข้าใจ spatial analysis
3. ใช้ rule-based extraction ก่อน

### Intermediate:
4. เพิ่ม AI integration
5. สร้าง template system
6. Implement hybrid mode

### Advanced:
7. Production optimization
8. API development
9. Monitoring & scaling

---

## 📚 Additional Prompts

### Create Custom Template:
```
สร้าง template สำหรับ [document type]:

Layout:
[อธิบายหรือแนบรูป]

Fields:
- field1: location, format
- field2: location, format

Output structure:
[JSON structure ที่ต้องการ]
```

### Add New OCR Engine:
```
เพิ่ม support สำหรับ [OCR engine]:

API: [link to docs]
Features: [list features]

ให้ compatible กับ OCR Adapter ที่มีอยู่
```

### Improve Accuracy:
```
Accuracy ต่ำสำหรับ [document type]:

ปัญหา:
- [describe issue]

ช่วย:
1. ปรับ spatial thresholds
2. ปรับ AI prompt
3. เพิ่ม validation
```

---

ใช้ prompts เหล่านี้เป็น **template** แล้วปรับแต่งตามความต้องการของคุณครับ! 🚀