"""
ตรวจสอบข้อมูล receipt ที่เรา test
"""
import json
from parallel_extraction import ReceiptSplitter

def main():
    # โหลด OCR file
    with open('output/ai_debug/requests/request_20251029_170728_909adbab.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    ocr_text = data['payload']['messages'][1]['content']

    # แยก receipts
    splitter = ReceiptSplitter()
    receipts = splitter.split_by_page_markers(ocr_text)

    # หา receipt แรกที่มี receipt number
    test_receipt = None
    for receipt in receipts:
        if receipt['receipt_number'] is not None:
            test_receipt = receipt
            break

    if not test_receipt:
        print("No receipt with receipt_number found")
        return

    print(f"Receipt ID: {test_receipt['receipt_id']}")
    print(f"Receipt Number: {test_receipt['receipt_number']}")
    print(f"Pages: {test_receipt['pages']}")
    print(f"OCR Length: {len(test_receipt['ocr_text'])}")

    print("\n--- OCR TEXT PREVIEW ---")
    print(test_receipt['ocr_text'][:500])
    print("...")

    # ตรวจสอบว่ามีข้อมูลอะไรใน OCR
    lines = test_receipt['ocr_text'].split('\n')

    hospital_names = []
    hns = []
    ans = []
    dates = []
    amounts = []
    billing_lines = []

    for line in lines:
        line_lower = line.lower()
        if 'hospital' in line_lower or 'โรงพยาบาล' in line:
            hospital_names.append(line.strip())
        if 'hn:' in line_lower or 'hn ' in line_lower:
            hns.append(line.strip())
        if 'an:' in line_lower or 'an ' in line_lower or 'en:' in line_lower or 'en ' in line_lower:
            ans.append(line.strip())
        if any(date_word in line_lower for date_word in ['date', 'วันที่', 'admission', 'visit']):
            dates.append(line.strip())
        if any(amount_word in line_lower for amount_word in ['amount', 'total', 'รวม']):
            amounts.append(line.strip())
        # ตรวจสอบ billing lines
        if '|' in line and any(char.isdigit() for char in line.split('|')[0] if char != ' '):
            billing_lines.append(line.strip())

    print("\n--- EXTRACTED INFO FROM OCR ---")
    print(f"Hospital names found: {len(hospital_names)}")
    for hn in hospital_names[:3]:
        print(f"  {hn}")

    print(f"HN found: {len(hns)}")
    for hn in hns[:3]:
        print(f"  {hn}")

    print(f"AN/EN found: {len(ans)}")
    for an in ans[:3]:
        print(f"  {an}")

    print(f"Dates found: {len(dates)}")
    for date in dates[:3]:
        print(f"  {date}")

    print(f"Amounts found: {len(amounts)}")
    for amt in amounts[:3]:
        print(f"  {amt}")

    print(f"Billing lines found: {len(billing_lines)}")
    for bl in billing_lines[:5]:
        print(f"  {bl}")

if __name__ == "__main__":
    main()
