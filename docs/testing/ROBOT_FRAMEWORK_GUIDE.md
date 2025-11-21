# 🤖 Robot Framework Automation Testing Guide

**สำหรับ:** การทดสอบ API แบบ Automation  
**เครื่องมือ:** Robot Framework + Selenium  
**วันที่:** 7 ตุลาคม 2568

---

## 📋 ภาพรวม

ระบบมี **2 ประเภทของ Robot Tests:**

1. **API Tests** (`robot_tests/api_tests.robot`)
   - ทดสอบ API endpoints โดยตรง
   - ไม่ต้องใช้ browser
   - รันเร็ว (< 1 นาที)

2. **Swagger UI Tests** (`robot_tests/swagger_ui_tests.robot`)
   - ทดสอบผ่าน Swagger UI (http://localhost:8888/docs)
   - ใช้ Selenium + Chrome
   - รันช้ากว่า (2-3 นาที)

---

## 🚀 การติดตั้ง

### **ติดตั้ง Robot Framework:**

```bash
# ติดตั้ง Robot Framework และ libraries
pip install -r requirements_robot.txt

# หรือติดตั้งทีละตัว
pip install robotframework
pip install robotframework-requests
pip install robotframework-jsonlibrary
pip install robotframework-seleniumlibrary
pip install selenium
pip install webdriver-manager
```

### **ติดตั้ง Chrome WebDriver (สำหรับ UI tests):**

```bash
# Windows
pip install webdriver-manager

# จะ download ChromeDriver อัตโนมัติตอนรัน
```

---

## 🧪 วิธีรัน Tests

### **Test 1: API Tests (แนะนำ - เร็ว)**

```bash
# รัน API tests ทั้งหมด
robot robot_tests/api_tests.robot

# หรือรันแบบระบุ tags
robot --include forms robot_tests/api_tests.robot
robot --include security robot_tests/api_tests.robot
```

**จะทดสอบ:**
- ✅ Health Check
- ✅ Authentication
- ✅ Form Classification (B01-B07) - ทั้ง 5 forms
- ✅ Security (Prompt Injection, SQL, XSS)
- ✅ Text Extraction
- ✅ Stats Authentication

**รวม: 12 test cases**

---

### **Test 2: Swagger UI Tests (ทดสอบ Web UI)**

```bash
# รัน Swagger UI tests
robot robot_tests/swagger_ui_tests.robot

# รันแบบ headless (ไม่เปิด browser)
robot --variable HEADLESS:true robot_tests/swagger_ui_tests.robot
```

**จะทดสอบ:**
- ✅ Swagger UI โหลดได้
- ✅ Endpoints แสดงครบ
- ✅ Try it out ทำงานได้
- ✅ Classification ทั้ง 5 forms
- ✅ Security tests

**รวม: 6 test cases**

---

### **Test 3: รัน Tests ทั้งหมด**

```bash
# รัน tests ทั้งหมดใน folder
robot robot_tests/

# Expected: 18 test cases (12 API + 6 UI)
```

---

## 📊 ผลลัพธ์ที่ได้

### **Console Output:**

```
==============================================================================
Robot Tests
==============================================================================
Robot Tests.Api Tests :: API Automation Tests for Medical Receipt Ex...
==============================================================================
TC001: Verify API Server is Running                             | PASS |
TC002: Authentication - Admin Login                             | PASS |
TC003: Classification - B01 Receipt-Bill                        | PASS |
TC004: Classification - B04 Invoice                             | PASS |
TC005: Classification - B05 Detail                              | PASS |
TC006: Classification - B06 Estimate/GOP                        | PASS |
TC007: Classification - B07 Statement                           | PASS |
TC008: Security - Prompt Injection Blocked                      | PASS |
TC009: Security - SQL Injection Blocked                         | PASS |
TC010: Security - XSS Attack Blocked                            | PASS |
TC011: Text Extraction                                          | PASS |
TC012: Statistics Endpoint Requires Auth                        | PASS |
------------------------------------------------------------------------------
Robot Tests.Api Tests                                           | PASS |
12 tests, 12 passed, 0 failed
==============================================================================
Robot Tests                                                     | PASS |
12 tests, 12 passed, 0 failed
==============================================================================
Output:  C:\Users\...\output.xml
Log:     C:\Users\...\log.html
Report:  C:\Users\...\report.html
```

---

### **HTML Reports:**

Robot Framework จะสร้าง 3 ไฟล์:

1. **`report.html`** - สรุปผลการทดสอบแบบ high-level
2. **`log.html`** - Log รายละเอียดทุก test case
3. **`output.xml`** - ข้อมูล XML สำหรับ CI/CD

**เปิดดู:**
```bash
# Windows
start report.html

# Mac/Linux
open report.html
```

---

## 🎯 Test Tags

### **รันแบบเลือก Tags:**

```bash
# รันเฉพาะ smoke tests
robot --include smoke robot_tests/

# รันเฉพาะ classification tests
robot --include forms robot_tests/

# รันเฉพาะ security tests
robot --include security robot_tests/

# รันเฉพาะ UI tests
robot --include ui robot_tests/

# รันหลาย tags
robot --include "forms OR security" robot_tests/
```

---

## 📊 Test Coverage

### **API Tests (12 tests):**

| Tag | Test Cases | Coverage |
|-----|-----------|----------|
| `smoke` | 1 | Health check |
| `auth` | 2 | Login + Stats auth |
| `forms` | 5 | B01, B04, B05, B06, B07 |
| `security` | 3 | Prompt, SQL, XSS |
| `extraction` | 1 | Text extraction |

### **UI Tests (6 tests):**

| Tag | Test Cases | Coverage |
|-----|-----------|----------|
| `ui` | 6 | All UI tests |
| `smoke` | 1 | UI loads |
| `endpoints` | 1 | All endpoints visible |
| `auth` | 1 | Login via UI |
| `classification` | 2 | B05 + All 5 forms |
| `security` | 1 | Prompt injection |

---

## 🎬 สำหรับการนำเสนอลูกค้า

### **Demo Script:**

```bash
# 1. เริ่ม API Server (Terminal 1)
python api_server.py

# 2. รัน Robot Tests (Terminal 2)
robot --outputdir robot_results robot_tests/api_tests.robot

# 3. แสดงผลลัพธ์
start robot_results/report.html
```

**ระหว่าง Demo:**
- 👀 ให้ลูกค้าดู Terminal (tests กำลังรัน)
- 📊 แสดง real-time results
- 📄 เปิด HTML report ให้ดู
- ✅ แสดงว่าผ่านทั้งหมด

---

## 🔧 Customization

### **เพิ่ม Test Cases ใหม่:**

```robot
*** Test Cases ***

TC_NEW: Your New Test
    [Documentation]    คำอธิบาย test ของคุณ
    [Tags]    custom
    
    ${response}=    GET    ${YOUR_URL}
    Status Should Be    200    ${response}
    
    Log    ✅ Your test passed
```

### **เปลี่ยน Variables:**

```robot
*** Variables ***
${BASE_URL}    http://your-server:port
${TIMEOUT}     20    # เพิ่ม timeout
```

---

## 📈 CI/CD Integration

### **Jenkins:**

```groovy
stage('API Tests') {
    steps {
        sh 'robot --outputdir results robot_tests/api_tests.robot'
    }
    post {
        always {
            robot outputPath: 'results'
        }
    }
}
```

### **GitHub Actions:**

```yaml
- name: Run Robot Framework Tests
  run: |
    pip install -r requirements_robot.txt
    robot --outputdir results robot_tests/api_tests.robot
    
- name: Upload Results
  uses: actions/upload-artifact@v2
  with:
    name: robot-results
    path: results/
```

---

## 🎯 Best Practices

### **DO ✅:**
- ใช้ meaningful test case names
- เพิ่ม [Documentation] ทุก test
- ใช้ [Tags] เพื่อจัดกลุ่ม
- เช็ค status codes
- Validate response structure

### **DON'T ❌:**
- Hard-code values
- Skip error handling
- ทดสอบหลายอย่างใน 1 test case
- ลืม cleanup

---

## 📊 Reports สำหรับลูกค้า

### **สร้าง Beautiful Reports:**

```bash
# รัน tests พร้อม custom report name
robot --outputdir demo_results \
      --name "Medical API Tests" \
      --reporttitle "API Automation Test Report" \
      --loglevel INFO \
      robot_tests/

# Report จะอยู่ที่:
# demo_results/report.html
```

**Report จะมี:**
- ✅ Test summary (passed/failed)
- ✅ รายละเอียดแต่ละ test
- ✅ Screenshots (สำหรับ UI tests)
- ✅ Execution time
- ✅ ตารางสรุป

---

## 🚀 Quick Start

### **1. ติดตั้ง:**
```bash
pip install -r requirements_robot.txt
```

### **2. เริ่ม API Server:**
```bash
python api_server.py
```

### **3. รัน Tests:**
```bash
# API Tests (เร็ว)
robot robot_tests/api_tests.robot

# UI Tests (ต้องมี Chrome)
robot robot_tests/swagger_ui_tests.robot
```

### **4. ดู Results:**
```bash
start report.html
```

---

## ✅ สรุป

### **สิ่งที่ได้:**
- ✅ **Robot Framework** automation tests
- ✅ **12 API test cases** (API endpoints)
- ✅ **6 UI test cases** (Swagger UI)
- ✅ **HTML reports** พร้อม screenshots
- ✅ **CI/CD ready** สำหรับ Jenkins, GitHub Actions

### **Test Coverage:**
- ✅ ทั้ง 5 Form IDs (B01-B07)
- ✅ Security tests (OWASP)
- ✅ Authentication
- ✅ Extraction
- ✅ Error handling

### **การใช้งาน:**
```bash
# รันทดสอบ
robot robot_tests/

# ดูผลลัพธ์
start report.html
```

---

**พร้อมสำหรับ Automation Testing แล้ว!** 🤖✅

**Version:** 1.0  
**Created:** October 7, 2025  
**Status:** ✅ Ready to Run

