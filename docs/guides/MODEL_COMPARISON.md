# AI Model Comparison - Two-Step Pipeline

## Test Environment
- **Pipeline**: Two-Step AI Extraction (Simple → Format)
- **Image**: KAL20240377371detail_1.png (Thai Medical Receipt)
- **OCR Engine**: OneOCR
- **Date**: 2025-10-03

## Models Tested

### 1. qwen/qwen3-4b-2507 ⭐ RECOMMENDED
- **Parameters**: 4 Billion
- **Provider**: Qwen
- **Specialization**: Multilingual, Efficient

### 2. openai/gpt-oss-20b
- **Parameters**: 20 Billion
- **Provider**: OpenAI
- **Specialization**: General Purpose

## Performance Results

| Metric | qwen3-4b-2507 | gpt-oss-20b | Winner |
|--------|---------------|-------------|--------|
| **OCR Time** | 2.28s | 2.25s | Tie |
| **AI Extraction Time** | 34.14s | 46.88s | ✅ qwen3-4b (26% faster) |
| **JSON Formatting** | 0.0001s | 0.0001s | Tie |
| **Total Time** | **36.42s** | **49.14s** | ✅ qwen3-4b (26% faster) |
| **Billing Items Extracted** | **24 items** | **15 items** | ✅ qwen3-4b (60% more) |
| **Hospital Name** | ✅ Correct | ✅ Correct | Tie |
| **HN** | ✅ Correct | ✅ Correct | Tie |
| **AN** | ✅ Correct | ✅ Correct | Tie |
| **Dates** | ✅ Correct | ✅ Correct | Tie |
| **Gross Amount** | ✅ Correct | ✅ Correct | Tie |
| **JSON Structure** | ✅ Valid | ✅ Valid | Tie |

## Detailed Analysis

### Speed Comparison
```
qwen3-4b-2507:  ████████████████████████████ 36.42s ⚡ FASTEST
gpt-oss-20b:    ████████████████████████████████████ 49.14s
```

### Completeness Comparison
```
qwen3-4b-2507:  ████████████████████████ 24 items ✅ MOST COMPLETE
gpt-oss-20b:    ███████████████ 15 items ⚠️ Missing 9 items
```

### Efficiency Score (Speed + Completeness)
```
qwen3-4b-2507:  ⭐⭐⭐⭐⭐ (5/5) EXCELLENT
gpt-oss-20b:    ⭐⭐⭐☆☆ (3/5) GOOD
```

## Missing Items in gpt-oss-20b

The following billing items were NOT extracted by gpt-oss-20b:
1. 1.1 - ค่ายาและสารอาหารทางหลอดเลือด
2. 1.2 - ค่าเวชภัณฑ์และอุปกรณ์
3. 1.4 - ค่าตรวจวินิจฉัยทางห้องปฏิบัติการ
4. 1.4.1 - ค่าตรวจวินิจฉัยทางห้องปฏิบัติการ
5. 1.6 - ค่าตรวจวินิจฉัยทางรังสีวิทยาและภาพการแพทย์
6. 1.6.1 - ค่าตรวจวินิจฉัย X-ray ทั่วไป
7. 1.11 - ค่าเครื่องมือทางการแพทย์
8. 1.14 - ค่าบริการทางการพยาบาล
9. 1.28 - ค่าผู้ประกอบวิชาชีพเวชกรรม

## Resource Usage

| Model | Parameters | Memory Usage | API Cost |
|-------|------------|--------------|----------|
| qwen3-4b-2507 | 4B | Lower | Lower |
| gpt-oss-20b | 20B | Higher | Higher |

## Recommendation

### ✅ Use qwen/qwen3-4b-2507 for:
- **Production deployments** - Faster, more reliable
- **High-volume processing** - Lower resource usage
- **Medical receipt extraction** - Better completeness
- **Cost-sensitive applications** - More efficient

### ⚠️ Consider gpt-oss-20b for:
- **Complex reasoning tasks** - If needed
- **When 15 items is acceptable** - If completeness is not critical
- **Specific use cases** - Where larger model is beneficial

## Conclusion

**Winner: qwen/qwen3-4b-2507**

The qwen3-4b model outperforms gpt-oss-20b in both speed and completeness:
- **26% faster** (36.42s vs 49.14s)
- **60% more complete** (24 items vs 15 items)
- **More efficient** (4B vs 20B parameters)
- **Better for production** (faster, cheaper, more complete)

For Thai medical receipt extraction using Two-Step AI Pipeline, qwen3-4b-2507 is the clear winner.

---

## Configuration

**Recommended settings in config.json:**
```json
{
  "ai_extraction": {
    "api": {
      "model": "qwen/qwen3-4b-2507",
      "timeout": 180,
      "max_retries": 2,
      "temperature": 0.1,
      "max_tokens": 8000
    }
  }
}
```

## Test Command

```bash
# Test with qwen3-4b
python test_two_step_pipeline.py KAL20240377371detail_1.png

# Test with gpt-oss (change model in config.json first)
python test_two_step_pipeline.py KAL20240377371detail_1.png
```

