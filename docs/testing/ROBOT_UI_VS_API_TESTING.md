# 🤖 Robot Framework: UI Testing vs API Testing

**คำถาม:** Robot Framework มี 2 แบบ แตกต่างกันอย่างไร?  
**วันที่:** 7 ตุลาคม 2568

---

## 🎯 ความแตกต่าง

### **API Testing (ทดสอบ API โดยตรง)**

**ไฟล์:** `robot_tests/simple_api_tests.robot`

**วิธีทำงาน:**
```
Robot → HTTP Request → API Server → Response → Robot
```

**ไม่ใช้ Browser** - เรียก API โดยตรงด้วย HTTP requests

**ตัวอย่าง:**
```robot
${response}=    POST    /classify    json={"texts":["..."]}
```

**ข้อดี:**
- ⚡ **เร็วมาก** (1-2 นาที, 12 tests)
- 💻 **ไม่ต้องใช้ Browser**
- 🎯 **ทดสอบ API logic โดยตรง**
- 🚀 **เหมาะสำหรับ CI/CD**

**ข้อเสีย:**
- ❌ ไม่ได้ทดสอบ UI
- ❌ ไม่เห็นหน้าจอ

---

### **UI Testing (ทดสอบผ่าน Swagger UI)**

**ไฟล์:** `robot_tests/swagger_ui_automation.robot`

**วิธีทำงาน:**
```
Robot → เปิด Chrome → ไปที่ /docs → คลิก → ใส่ข้อมูล → Execute → ดู Response
```

**ใช้ Browser จริง** - Robot ควบคุม browser และคลิกเหมือนคน

**ตัวอย่าง:**
```robot
Click Element    xpath=//span[text()='/classify']
Click Element    xpath=//button[text()='Try it out']
Input Text    css:textarea    {"texts":["..."]}
Click Element    xpath=//button[text()='Execute']
```

**ข้อดี:**
- 👀 **เห็นหน้าจอ** - ดู browser ทำงานจริง
- ✅ **ทดสอบ UI** - ทดสอบว่า Swagger UI ใช้งานได้
- 🎬 **สำหรับ Demo** - ลูกค้าเห็นภาพชัดเจน
- 📸 **มี Screenshots** - บันทึกภาพทุกขั้นตอน

**ข้อเสีย:**
- 🐢 **ช้ากว่า** (3-5 นาที, 6 tests)
- 💻 **ต้องมี Chrome** installed
- 🔧 **Setup ยุ่งกว่า**

---

## 📊 เปรียบเทียบ

| Feature | API Testing | UI Testing |
|---------|-------------|------------|
| **เปิด Browser** | ❌ ไม่เปิด | ✅ เปิด Chrome |
| **คลิกใน UI** | ❌ ไม่คลิก | ✅ คลิกจริง |
| **ความเร็ว** | ⚡ เร็ว (1-2 นาที) | 🐢 ช้า (3-5 นาที) |
| **Screenshots** | ❌ ไม่มี | ✅ มี |
| **เหมาะสำหรับ** | CI/CD, Regression | Demo, UAT |
| **ไฟล์** | `simple_api_tests.robot` | `swagger_ui_automation.robot` |

---

## 🎬 UI Automation Demo

### **รัน UI Automation:**

```bash
# Robot จะเปิด Chrome และคลิกเองทั้งหมด
robot robot_tests/swagger_ui_automation.robot
```

**สิ่งที่จะเห็น:**

1. 🌐 **Chrome เปิดอัตโนมัติ**
2. 🔗 **ไปที่ http://localhost:8888/docs**
3. 🖱️ **Robot scroll หา endpoint**
4. 🖱️ **Robot คลิก "Try it out"**
5. ⌨️ **Robot พิมพ์ JSON data**
6. 🖱️ **Robot คลิก "Execute"**
7. ✅ **Robot ตรวจสอบ response**
8. 📸 **บันทึก screenshot**
9. ✅ **PASS/FAIL**

**ลูกค้าจะเห็น:**
- 👀 Browser เปิดและทำงานเอง
- 🎯 เหมือนคนทดสอบด้วยมือ
- 📸 Screenshots ทุกขั้นตอน
- ✅ ผลการทดสอบ

---

## 🚀 วิธีรัน UI Automation

### **ข้อกำหนด:**

```bash
# ติดตั้ง Selenium และ Chrome WebDriver
pip install robotframework-seleniumlibrary
pip install webdriver-manager

# ต้องมี Google Chrome installed
```

### **รัน Tests:**

```bash
# แบบเห็น Browser (แนะนำสำหรับ Demo)
robot robot_tests/swagger_ui_automation.robot

# แบบ Headless (ไม่เปิด browser)
robot --variable HEADLESS:true robot_tests/swagger_ui_automation.robot
```

---

## 📸 Screenshots ที่จะได้

Robot จะบันทึก screenshots อัตโนมัติ:

```
robot_results/selenium-screenshot-*.png
01_swagger_loaded.png          # Swagger UI โหลดเสร็จ
02_login_input.png             # ใส่ข้อมูล login
03_login_response.png          # ผลลัพธ์ login
04_b05_input.png               # ใส่ข้อมูล B05
05_b05_response.png            # ผลลัพธ์ B05 (ref_code, form_id)
06_b01_response.png            # ผลลัพธ์ B01
07_b06_response.png            # ผลลัพธ์ B06
08_security_blocked.png        # Security test ถูกบล็อก
```

**สำหรับลูกค้า:**
- 📊 แสดงใน HTML report
- 📸 ดูได้ทีละภาพ
- ✅ เป็นหลักฐานการทดสอบ

---

## 🎯 Tests ที่มีใน UI Automation

### **6 UI Test Cases:**

1. ✅ **UI Test 01:** Swagger UI loads successfully
2. ✅ **UI Test 02:** Login via Swagger UI (Robot คลิกเอง)
3. ✅ **UI Test 03:** Classification B05 (Robot คลิกเอง)
4. ✅ **UI Test 04:** Classification B01 (Robot คลิกเอง)
5. ✅ **UI Test 05:** Classification B06 (Robot คลิกเอง)
6. ✅ **UI Test 06:** Security test (Robot คลิกเอง)

**แต่ละ test:**
- Robot เปิด browser
- Robot ไปที่ Swagger UI
- Robot คลิก endpoint
- Robot คลิก "Try it out"
- Robot ใส่ JSON data
- Robot คลิก "Execute"
- Robot ตรวจสอบ response
- Robot บันทึก screenshot

---

## 🎬 การนำเสนอให้ลูกค้า

### **Option 1: API Testing (เร็ว)**

```bash
robot robot_tests/simple_api_tests.robot
# ใช้เวลา: 1-2 นาที
# Tests: 12 tests
# แสดง: Console output
```

**เหมาะสำหรับ:**
- ✅ Quick demo
- ✅ CI/CD demonstration
- ✅ Technical audience

---

### **Option 2: UI Testing (Demo น่าสนใจ)** ⭐ แนะนำ

```bash
robot robot_tests/swagger_ui_automation.robot
# ใช้เวลา: 3-5 นาที
# Tests: 6 tests
# แสดง: Browser เปิดและคลิกเอง + Screenshots
```

**เหมาะสำหรับ:**
- ✅ **Client presentation**
- ✅ **UAT demonstration**
- ✅ **Non-technical audience**
- ✅ **สร้างความประทับใจ**

**ลูกค้าจะเห็น:**
- 🌐 Browser เปิดเอง
- 🖱️ Robot คลิกเอง
- ⌨️ Robot พิมพ์เอง
- ✅ ทดสอบครบ 5 forms
- 🔒 ทดสอบ security
- 📸 มี screenshots หลักฐาน

---

## 📋 สรุปทั้ง 2 แบบ

### **ระบบมีทั้งหมด 3 ระดับ:**

#### **Level 1: Python Scripts**
```bash
python quick_api_test.py
```
- เร็วที่สุด (30 วินาที)
- ไม่เปิด browser
- 11 tests

#### **Level 2: Robot API Testing**
```bash
robot robot_tests/simple_api_tests.robot
```
- เร็ว (1-2 นาที)
- ไม่เปิด browser
- 12 tests
- มี HTML report

#### **Level 3: Robot UI Automation** ⭐
```bash
robot robot_tests/swagger_ui_automation.robot
```
- ช้าหน่อย (3-5 นาที)
- **เปิด browser และคลิกเอง** 🎯
- 6 tests
- มี screenshots
- **เหมาะสำหรับ demo ให้ลูกค้า!**

---

## ✅ คำสั่งที่ต้องรัน

### **สำหรับ UI Automation (ที่คุณถาม):**

```bash
# 1. ติดตั้ง dependencies
pip install robotframework-seleniumlibrary

# 2. รัน UI automation
robot robot_tests/swagger_ui_automation.robot

# 3. ดู report
start robot_results/report.html
```

**Robot จะ:**
- ✅ เปิด Chrome เอง
- ✅ ไปที่ Swagger UI เอง
- ✅ คลิกทดสอบเอง
- ✅ บันทึก screenshots
- ✅ แสดงผลใน HTML report

---

**นี่คือ UI Automation ที่คุณต้องการ!** 🤖🌐✅

**รันคำสั่งนี้:**
```bash
robot robot_tests/swagger_ui_automation.robot
```
