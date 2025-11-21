"""
วิเคราะห์ OCR text เพื่อดูโครงสร้างของ receipts
"""
import json
import re

def main():
    # โหลด OCR file
    print("Loading OCR file...")
    with open('output/ai_debug/requests/request_20251029_170728_909adbab.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    ocr_text = data['payload']['messages'][1]['content']
    print(f"Loaded OCR text: {len(ocr_text)} characters")

    lines = ocr_text.split('\n')
    print(f"Total lines: {len(lines)}")

    # นับจำนวน 'หน้าที่' markers
    page_markers = []
    for i, line in enumerate(lines):
        if line.startswith('หน้าที่'):
            try:
                page_num = int(line.split()[1])
                page_markers.append((i, page_num))
            except (IndexError, ValueError):
                continue

    print(f"\nFound {len(page_markers)} page markers:")
    for i, (line_idx, page_num) in enumerate(page_markers[:15]):  # แสดงแค่ 15 ตัวแรก
        print(f"  Page {page_num} at line {line_idx}")

    # นับจำนวน Receipt Number patterns (หาเลขที่แท้จริง)
    receipt_patterns = []
    for i, line in enumerate(lines):
        if 'Receipt Number' in line or 'Receipt Numoer' in line or 'Receipt Numbel' in line:
            # หาเลข 10 หลักที่ขึ้นต้นด้วย 228 หรือ 2280
            matches = re.findall(r'\b(228\d{7})\b', line)
            for match in matches:
                receipt_patterns.append((i, match))

    print(f"\nFound {len(receipt_patterns)} receipt numbers:")
    for i, (line_idx, receipt_num) in enumerate(receipt_patterns[:15]):  # แสดงแค่ 15 ตัวแรก
        print(f"  Receipt {receipt_num} at line {line_idx}")

    # วิเคราะห์ pattern ของ receipts
    print(f"\nAnalyzing receipt patterns:")
    print(f"  Total pages in document: {len(page_markers)}")
    print(f"  Total receipts detected: {len(receipt_patterns)}")

    if page_markers and receipt_patterns:
        print("\nReceipt structure analysis:")
        # แต่ละ receipt ควรมี 2 หน้า (Original + Copy)
        expected_receipts = len(page_markers) // 2
        print(f"  Expected receipts (pages/2): {expected_receipts}")
        print(f"  Detected receipts: {len(receipt_patterns)}")

        # ตรวจสอบว่าทุก receipt มี receipt number หรือไม่
        receipt_numbers = set()
        for _, receipt_num in receipt_patterns:
            receipt_numbers.add(receipt_num)
        print(f"  Unique receipt numbers: {len(receipt_numbers)}")

if __name__ == "__main__":
    main()
