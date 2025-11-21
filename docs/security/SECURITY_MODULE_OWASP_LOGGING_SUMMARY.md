# Security Module - OWASP LLM Top 10 Logging Enhancement

## สรุปการปรับปรุง
เพิ่ม **OWASP LLM Top 10 Category** ลงใน log ทุกครั้งที่มีการตรวจสอบความปลอดภัย เพื่อให้ระบุได้ชัดเจนว่าการตรวจสอบแต่ละครั้งป้องกันช่องโหว่ตามมาตรฐาน OWASP ข้อไหน

## การเปลี่ยนแปลงทั้งหมด

### 1. SecurityValidator Class

#### 1.1 Prompt Injection Detection (LLM01)
```python
# เดิม
logger.warning(f"Prompt injection detected: {pattern}")

# ใหม่
logger.warning(f"[OWASP LLM01: Prompt Injection] Detected pattern: {pattern}")
```

**ข้อดี:**
- ระบุชัดเจนว่าเป็นการป้องกัน Prompt Injection
- แสดง pattern ที่ตรวจพบ
- ง่ายต่อการค้นหาและวิเคราะห์ log

#### 1.2 SQL Injection Detection (LLM02)
```python
# เดิม
logger.warning(f"SQL injection detected: {pattern}")

# ใหม่
logger.warning(f"[OWASP LLM02: Insecure Output Handling] SQL injection pattern detected: {pattern}")
```

**ข้อดี:**
- ระบุว่าเป็นการป้องกัน Insecure Output Handling
- ช่วยติดตามความพยายามในการ inject SQL commands

#### 1.3 Path Traversal Detection (LLM03)
```python
# เดิม
logger.warning(f"Path traversal detected: {pattern}")

# ใหม่
logger.warning(f"[OWASP LLM03: Training Data Poisoning] Path traversal pattern detected: {pattern}")
```

**ข้อดี:**
- ป้องกันการเข้าถึงไฟล์ที่ไม่ได้รับอนุญาต
- เกี่ยวข้องกับการป้องกัน Training Data Poisoning

#### 1.4 File Upload Validation (LLM03 & LLM06)
```python
# Filename validation
logger.warning(f"[OWASP LLM03: Training Data Poisoning] Invalid filename detected: {filename}")

# File size validation
logger.warning(f"[OWASP LLM06: Excessive Agency] File too large: {file_size} bytes")

# Content type validation
logger.warning(f"[OWASP LLM03: Training Data Poisoning] Disallowed content type: {content_type}")

# File extension validation
logger.warning(f"[OWASP LLM03: Training Data Poisoning] Disallowed file extension: {file_ext}")
```

**ข้อดี:**
- ป้องกันการอัพโหลดไฟล์ที่เป็นอันตราย
- ควบคุมขนาดไฟล์เพื่อป้องกัน resource exhaustion

### 2. RateLimiter Class (LLM06 & LLM09)

```python
# Per-minute rate limit
logger.warning(f"[OWASP LLM06: Excessive Agency & LLM09: Overreliance] Rate limit exceeded for client {client_id} - {len(recent_requests)} requests in last minute")

# Per-hour rate limit
logger.warning(f"[OWASP LLM06: Excessive Agency & LLM09: Overreliance] Hourly rate limit exceeded for client {client_id} - {len(self.requests[client_id])} requests in last hour")
```

**ข้อดี:**
- แสดงจำนวน requests ที่เกินขั้นสูง
- ป้องกัน DDoS และ abuse
- ระบุ client_id เพื่อการติดตาม

### 3. AuthenticationManager Class (LLM08)

#### 3.1 Token Signature Validation
```python
logger.warning(f"[OWASP LLM08: Excessive Agency] Invalid token signature detected")
```

#### 3.2 Token Expiration Check
```python
logger.warning(f"[OWASP LLM08: Excessive Agency] Expired token detected for user: {token_data.get('user_id', 'unknown')}")
```

#### 3.3 Token Record Check
```python
logger.warning(f"[OWASP LLM08: Excessive Agency] Token not found in records")
```

#### 3.4 Token Validation Error
```python
logger.error(f"[OWASP LLM08: Excessive Agency] Token validation error: {e}")
```

#### 3.5 Permission Check
```python
logger.warning(f"[OWASP LLM08: Excessive Agency] Permission denied for user {token_data.get('user_id', 'unknown')}: required '{required_permission}'")
```

**ข้อดี:**
- ติดตามความพยายามในการใช้ token ที่ไม่ถูกต้อง
- ระบุ user_id เพื่อการตรวจสอบ
- แสดง permission ที่ต้องการแต่ไม่ได้รับอนุญาต

### 4. SecurityLogger Class

#### 4.1 Enhanced log_security_event Method
```python
@staticmethod
def log_security_event(event_type: str, details: Dict[str, Any], severity: str = "INFO", owasp_category: str = None):
    """
    Log security-related events
    
    Args:
        event_type: Type of security event
        details: Event details
        severity: Log severity level
        owasp_category: OWASP LLM Top 10 category (if applicable)
    """
```

**การเปลี่ยนแปลง:**
- เพิ่ม parameter `owasp_category` (optional)
- เพิ่ม `owasp_category` ลงใน log entry
- แสดง prefix `[{owasp_category}]` ใน log message

#### 4.2 Enhanced log_attack_attempt Method
```python
@staticmethod
def log_attack_attempt(attack_type: str, client_ip: str, details: Dict[str, Any], owasp_category: str = None):
    """
    Log attack attempts
    
    Args:
        attack_type: Type of attack
        client_ip: Client IP address
        details: Attack details
        owasp_category: OWASP LLM Top 10 category (if applicable)
    """
    # Auto-detect OWASP category based on attack type
    if not owasp_category:
        attack_type_lower = attack_type.lower()
        if "prompt" in attack_type_lower or "injection" in attack_type_lower:
            owasp_category = "OWASP LLM01: Prompt Injection"
        elif "sql" in attack_type_lower or "xss" in attack_type_lower:
            owasp_category = "OWASP LLM02: Insecure Output Handling"
        elif "path" in attack_type_lower or "traversal" in attack_type_lower:
            owasp_category = "OWASP LLM03: Training Data Poisoning"
        elif "rate" in attack_type_lower or "dos" in attack_type_lower:
            owasp_category = "OWASP LLM06: Excessive Agency"
```

**ข้อดี:**
- Auto-detect OWASP category จาก attack type
- รองรับการระบุ category แบบ manual
- เพิ่มความยืดหยุ่นในการใช้งาน

### 5. PromptInjectionDetector Class (LLM01)

#### 5.1 Enhanced detect_prompt_injection Method
```python
@classmethod
def detect_prompt_injection(cls, text: str, log_detection: bool = True) -> Tuple[bool, List[str]]:
```

**การเปลี่ยนแปลง:**
- เพิ่ม parameter `log_detection` (default: True)
- Log ทุกครั้งที่พบ advanced pattern:
  ```python
  logger.warning(f"[OWASP LLM01: Prompt Injection] Advanced pattern detected: {pattern}")
  ```
- Log เมื่อพบ suspicious repetition:
  ```python
  logger.warning(f"[OWASP LLM01: Prompt Injection] Suspicious repetition detected: max_count={max_count}, total_words={len(words)}")
  ```
- Log เมื่อพบ excessive punctuation:
  ```python
  logger.warning(f"[OWASP LLM01: Prompt Injection] Excessive punctuation detected: {punct_count}/{len(text)} characters")
  ```
- Log เมื่อพบ encoding attempts:
  ```python
  logger.warning(f"[OWASP LLM01: Prompt Injection] Encoding attempt detected in input")
  ```

**ข้อดี:**
- Log รายละเอียดเพิ่มเติมสำหรับการวิเคราะห์
- สามารถปิด logging ได้ถ้าไม่ต้องการ (log_detection=False)
- ช่วยในการตรวจสอบและปรับปรุง detection patterns

## OWASP LLM Top 10 Coverage

### ✅ LLM01: Prompt Injection
- `SecurityValidator.validate_input()` - Basic patterns
- `PromptInjectionDetector.detect_prompt_injection()` - Advanced patterns
- Log แสดง pattern ที่ตรวจพบ

### ✅ LLM02: Insecure Output Handling
- `SecurityValidator.validate_input()` - SQL injection patterns
- Log แสดง SQL injection patterns

### ✅ LLM03: Training Data Poisoning
- `SecurityValidator.validate_input()` - Path traversal patterns
- `SecurityValidator.validate_file_upload()` - File validation
- Log แสดง filename, content type, และ extension ที่ไม่ถูกต้อง

### ✅ LLM06: Excessive Agency
- `RateLimiter.is_allowed()` - Rate limiting
- `SecurityValidator.validate_file_upload()` - File size limit
- Log แสดงจำนวน requests และขนาดไฟล์

### ✅ LLM08: Excessive Agency
- `AuthenticationManager.validate_token()` - Token validation
- `AuthenticationManager.has_permission()` - Permission check
- Log แสดง user_id และ permission details

### ✅ LLM09: Overreliance
- `RateLimiter.is_allowed()` - Prevent excessive API usage
- Log แสดงจำนวน requests ที่เกินขั้น

## ตัวอย่าง Log Output

### Prompt Injection Detection
```
WARNING - [OWASP LLM01: Prompt Injection] Detected pattern: ignore\s+previous\s+instructions
WARNING - [OWASP LLM01: Prompt Injection] Advanced pattern detected: (jailbreak|escape|break\\s+free)
WARNING - [OWASP LLM01: Prompt Injection] Suspicious repetition detected: max_count=15, total_words=40
WARNING - [OWASP LLM01: Prompt Injection] Excessive punctuation detected: 120/300 characters
WARNING - [OWASP LLM01: Prompt Injection] Encoding attempt detected in input
```

### SQL Injection Detection
```
WARNING - [OWASP LLM02: Insecure Output Handling] SQL injection pattern detected: union\s+select
WARNING - [OWASP LLM02: Insecure Output Handling] SQL injection pattern detected: drop\s+table
```

### Path Traversal Detection
```
WARNING - [OWASP LLM03: Training Data Poisoning] Path traversal pattern detected: \.\./
WARNING - [OWASP LLM03: Training Data Poisoning] Invalid filename detected: ../../etc/passwd
WARNING - [OWASP LLM03: Training Data Poisoning] Disallowed content type: application/x-executable
WARNING - [OWASP LLM03: Training Data Poisoning] Disallowed file extension: .exe
```

### Rate Limiting
```
WARNING - [OWASP LLM06: Excessive Agency & LLM09: Overreliance] Rate limit exceeded for client 192.168.1.100 - 61 requests in last minute
WARNING - [OWASP LLM06: Excessive Agency & LLM09: Overreliance] Hourly rate limit exceeded for client 192.168.1.100 - 1001 requests in last hour
```

### Authentication & Authorization
```
WARNING - [OWASP LLM08: Excessive Agency] Invalid token signature detected
WARNING - [OWASP LLM08: Excessive Agency] Expired token detected for user: user_12345
WARNING - [OWASP LLM08: Excessive Agency] Token not found in records
WARNING - [OWASP LLM08: Excessive Agency] Permission denied for user user_12345: required 'admin'
ERROR - [OWASP LLM08: Excessive Agency] Token validation error: Invalid token format
```

### Security Events with OWASP Category
```
CRITICAL - SECURITY: [OWASP LLM01: Prompt Injection] ATTACK_ATTEMPT_PROMPT_INJECTION - {'client_ip': '192.168.1.100', 'attack_details': {...}}
CRITICAL - SECURITY: [OWASP LLM02: Insecure Output Handling] ATTACK_ATTEMPT_SQL_INJECTION - {'client_ip': '192.168.1.100', 'attack_details': {...}}
```

## ประโยชน์ของการปรับปรุง

### 1. การตรวจสอบและวิเคราะห์
- **ค้นหาง่าย:** สามารถค้นหา log ตาม OWASP category ได้ทันที
  ```bash
  grep "OWASP LLM01" logs/*.log
  grep "OWASP LLM02" logs/*.log
  ```
- **สถิติ:** สามารถนับจำนวนการโจมตีแต่ละประเภทได้
- **Trend Analysis:** วิเคราะห์แนวโน้มการโจมตีในแต่ละช่วงเวลา

### 2. การตอบสนองต่อเหตุการณ์ (Incident Response)
- **ระบุชัดเจน:** รู้ทันทีว่าเป็นการโจมตีแบบไหน
- **ดำเนินการเร็วขึ้น:** มีข้อมูลครบถ้วนในการตัดสินใจ
- **Documentation:** มี evidence ชัดเจนสำหรับรายงาน

### 3. การตรวจสอบความสอดคล้อง (Compliance)
- **OWASP Compliance:** แสดงให้เห็นว่าระบบมีการป้องกันตาม OWASP LLM Top 10
- **Audit Trail:** มี log ครบถ้วนสำหรับการตรวจสอบ
- **Report Generation:** สามารถสร้างรายงานความปลอดภัยได้อัตโนมัติ

### 4. การพัฒนาและปรับปรุง
- **Identify Patterns:** ระบุ attack patterns ที่พบบ่อย
- **Improve Detection:** ปรับปรุง detection rules ตาม log analysis
- **Performance Tuning:** ดู false positives และปรับแต่ง

### 5. การฝึกอบรมและการศึกษา
- **Learning Tool:** ใช้ log เป็นตัวอย่างในการฝึกอบรม
- **Best Practices:** แสดง best practices ในการจัดการความปลอดภัย
- **Documentation:** เป็นเอกสารอ้างอิงสำหรับทีม

## การใช้งาน Log Analysis

### 1. Real-time Monitoring
```bash
# ดู log แบบ real-time
tail -f logs/api_server.log | grep "OWASP"

# ดูเฉพาะ Prompt Injection
tail -f logs/api_server.log | grep "LLM01"

# ดูเฉพาะ CRITICAL events
tail -f logs/api_server.log | grep "CRITICAL" | grep "OWASP"
```

### 2. Historical Analysis
```bash
# นับจำนวนการโจมตีแต่ละประเภท
grep -c "OWASP LLM01" logs/api_server.log
grep -c "OWASP LLM02" logs/api_server.log
grep -c "OWASP LLM03" logs/api_server.log

# หา Top 10 IP ที่โจมตีบ่อยสุด
grep "OWASP" logs/api_server.log | grep -oP "client_id': '\K[^']+" | sort | uniq -c | sort -rn | head -10
```

### 3. Python Script สำหรับ Log Analysis
```python
import re
from collections import Counter
from datetime import datetime

def analyze_security_logs(log_file):
    """วิเคราะห์ security logs"""
    owasp_counts = Counter()
    attack_times = []
    
    with open(log_file, 'r') as f:
        for line in f:
            # Count OWASP categories
            if 'OWASP LLM' in line:
                match = re.search(r'OWASP LLM\d+', line)
                if match:
                    owasp_counts[match.group()] += 1
                    
                # Extract timestamp
                time_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                if time_match:
                    attack_times.append(time_match.group())
    
    # Print summary
    print("=== OWASP LLM Top 10 Detection Summary ===")
    for category, count in owasp_counts.most_common():
        print(f"{category}: {count} detections")
    
    print(f"\nTotal attacks detected: {sum(owasp_counts.values())}")
    print(f"Time range: {min(attack_times)} to {max(attack_times)}")

# Usage
analyze_security_logs('logs/api_server.log')
```

## Backward Compatibility

การเปลี่ยนแปลงทั้งหมดเป็น **backward compatible**:
- เพิ่ม optional parameters เท่านั้น
- ไม่ทำให้ code เดิมใช้งานไม่ได้
- สามารถใช้งาน SecurityLogger แบบเดิมได้ปกติ

## สรุป

การเพิ่ม **OWASP LLM Top 10 Category** ลงใน log ทำให้:
1. ✅ **ติดตามได้ชัดเจน** - รู้ทันทีว่าเป็นการโจมตีประเภทไหน
2. ✅ **วิเคราะห์ง่าย** - สามารถสร้างรายงานและสถิติได้อัตโนมัติ
3. ✅ **ตอบสนองเร็ว** - มีข้อมูลครบถ้วนในการดำเนินการ
4. ✅ **Compliance** - แสดงการป้องกันตาม OWASP LLM Top 10
5. ✅ **ปรับปรุงต่อเนื่อง** - ใช้ log เป็นข้อมูลในการพัฒนา

---

**Updated:** October 15, 2025  
**Version:** 2.0  
**Module:** security_module.py

