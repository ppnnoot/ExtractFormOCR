# 🔄 คำสั่ง Restart API Server

**สถานการณ์:** แก้ไข code แล้ว ต้อง restart เพื่อให้มีผล  
**เวลาที่ใช้:** 10 วินาที

---

## 🚀 วิธี Restart (Windows)

### **ขั้นที่ 1: หยุด Server เดิม**

ไปที่ Terminal/PowerShell ที่รัน `python api_server.py`

**กด:** `Ctrl+C`

จะเห็นข้อความ:
```
^C
INFO:     Shutting down
INFO:     Finished server process
```

---

### **ขั้นที่ 2: เริ่ม Server ใหม่**

```bash
python api_server.py
```

**รอจนเห็นข้อความ:**
```
INFO:     Uvicorn running on http://0.0.0.0:8888 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

✅ **พร้อมใช้งาน!**

---

### **ขั้นที่ 3: Clear Browser Cache & Reload**

**เปิด Browser:**
```
http://localhost:8888/docs
```

**Clear Cache และ Reload:**
- Windows: `Ctrl+Shift+R` (Hard Reload)
- Mac: `Cmd+Shift+R`

หรือ:
- กด `F12` → เปิด DevTools
- คลิกขวาที่ปุ่ม Refresh
- เลือก "Empty Cache and Hard Reload"

---

## ✅ ตรวจสอบว่า Restart สำเร็จ

### **Test 1: Health Check**
```bash
curl http://localhost:8888/health
```

**Expected:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "..."
}
```

---

### **Test 2: Swagger UI**
```
http://localhost:8888/docs
```

**ควรเห็น:**
- ✅ UI สวยงาม (ไม่ขาด CSS)
- ✅ ไม่มี error ใน Console
- ✅ มีปุ่ม "Try it out" ทำงานได้

---

### **Test 3: Quick API Test**
```bash
python quick_api_test.py
```

**Expected:**
```
Total Tests: 11
✅ Passed: 11 (100%)
```

---

## 🔍 ถ้ายังมี Error

### **1. ตรวจสอบ Console ใน Browser**

กด `F12` → ดูแท็บ "Console"

**ถ้ายังเห็น CSP errors:**
- ลอง Hard Reload: `Ctrl+Shift+R`
- ลองปิดแล้วเปิด browser ใหม่
- ลองใช้ Incognito Mode

---

### **2. ตรวจสอบว่า Code ใหม่โหลดแล้ว**

```bash
# ดู log ตอนเริ่ม server
# ควรเห็น:
INFO: Two-Step AI Pipeline initialized successfully
INFO: Document Classifier initialized successfully
```

---

### **3. ตรวจสอบ Security Headers**

```bash
# ดู headers ของ /docs
curl -I http://localhost:8888/docs | grep -i "content-security"
```

**ควรเห็น CSP ที่อนุญาต CDN:**
```
Content-Security-Policy: default-src 'self' https://cdn.jsdelivr.net https://fastapi.tiangolo.com; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; ...
```

---

## 🎯 Quick Restart Command

**One-liner:**
```bash
# หยุดแล้วเริ่มใหม่
# กด Ctrl+C แล้ว:
python api_server.py
```

---

## ✅ Checklist

- [ ] กด Ctrl+C หยุด server เดิม
- [ ] รัน `python api_server.py` ใหม่
- [ ] เห็นข้อความ "Application startup complete"
- [ ] เปิด http://localhost:8888/docs
- [ ] กด Ctrl+Shift+R (Hard Reload)
- [ ] Swagger UI แสดงปกติ ไม่มี CSP errors

---

**หลังจาก Restart แล้ว Swagger UI จะทำงานได้ปกติ!** ✅🚀

