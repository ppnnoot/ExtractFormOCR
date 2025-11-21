# ⚙️ Setup & Configuration

เอกสารการติดตั้งและการตั้งค่าระบบ

## 📋 เอกสารในโฟลเดอร์นี้

### Installation Guides
- `SETUP_GUIDE.md` - คู่มือติดตั้งหลัก
- `QUICK_START.md` - เริ่มต้นใช้งานแบบเร็ว
- `ONECR_SETUP.md` - ติดตั้ง OneOCR Library
- `ONECR_INTEGRATION_SUMMARY.md` - สรุปการ integrate OneOCR

### Configuration
- `CONFIG_COMPARISON.md` - เปรียบเทียบ Configuration

### Restart & Troubleshooting
- `RESTART_INSTRUCTIONS.md` - วิธีการ restart ระบบ
- `URGENT_RESTART_NEEDED.md` - เมื่อต้อง restart ด่วน

## 🎯 เริ่มต้นที่นี่

1. **ติดตั้งระบบ** - `SETUP_GUIDE.md`
2. **เริ่มต้นแบบเร็ว** - `QUICK_START.md`
3. **ติดตั้ง OneOCR** - `ONECR_SETUP.md`

## 📦 Requirements

### Python Dependencies
```bash
pip install -r requirements.txt
```

### System Requirements
- Python 3.8+
- 8GB+ RAM
- Windows/Linux/macOS

## 🚀 Quick Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd ExtractForm

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup configuration
cp config.example.json config.json

# 4. Start API server
python api_server.py
```

## ⚙️ Configuration Files

- `config.json` - Main configuration
- `requirements.txt` - Python dependencies
- `requirements_robot.txt` - Robot Framework dependencies

## 🔧 Services

### API Server
```bash
python api_server.py --port 8888
```

### OneOCR (Optional)
- ติดตั้งตามคู่มือ `ONECR_SETUP.md`

---
**หมวดหมู่:** Setup & Installation

