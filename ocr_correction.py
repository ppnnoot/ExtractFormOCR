"""
OCR Text Correction Module
แก้ไขข้อผิดพลาดที่เกิดจาก OCR ก่อนส่งไปยัง API เพื่อเพิ่มความแม่นยำ
"""

import re
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class OCRCorrectionManager:
    """จัดการการแก้ไขข้อผิดพลาด OCR"""

    def __init__(self):
        # Common OCR character misrecognitions (Thai)
        self.char_corrections = {
            # Common Thai character substitutions
            'ดูขวาง': 'คูขวาง',  # Road name correction
            'ดูขวง': 'คูขวง',
            'ดูขวา': 'คูขวา',
            'ดูขา': 'คูขา',

            # Medical terms corrections
            'ยาผู้ป่วยใน': 'ยาผู้ป่วยใน',
            'ยาผู้ป่วยกลมบ': 'ยาผู้ป่วยกลับบ้าน',
            'ยาผู้ป่วยกลมบ': 'ยาผู้ป่วยกลับบ้าน',
            'ยาผู้ป่วยกลมบา': 'ยาผู้ป่วยกลับบ้าน',
            'ยาผู้ป่วยกลบ': 'ยาผู้ป่วยกลับบ้าน',

            # Receipt terminology
            'ใบแจ้งยอดค่ารักษาพยาบาล': 'ใบแจ้งยอดค่ารักษาพยาบาล',
            'ใบแจ้งยอดค่ารกษาพยาบาล': 'ใบแจ้งยอดค่ารักษาพยาบาล',
            'ใบแจงยอด': 'ใบแจ้งยอด',

            # Common OCR misreads
            'Numbel': 'Number',
            'Numoer': 'Number',
            'Numbe1': 'Number',
            'Num0er': 'Number',

            # Hospital terms
            'โรงพยาบาล': 'โรงพยาบาล',
            'โจงพยาบาล': 'โรงพยาบาล',
            'โรงพยาบาล': 'โรงพยาบาล',

            # Common OCR artifacts
            'ี': 'ี',  # Remove artifacts
            '่': '่',
            '้': '้',
            '๊': '๊',
            '๋': '๋',

            # Date/time corrections
            'ว/ด': 'วดป',
            'วันที่': 'วันที่',
            'เวลา': 'เวลา',

            # Number corrections
            'O': '0',  # Common digit misrecognition
            'o': '0',
            'l': '1',
            'I': '1',
            'เ1': '11',
            'เธอ': '30',
            'เอ': '8',
            'เอา': '8',
            'เออ': '8',
        }

        # Medical billing code corrections
        self.billing_code_corrections = {
            '1.1.1(1)': '1.1.1(1)',
            '1.1.1(2)': '1.1.1(2)',
            '1.1.2(1)': '1.1.2(1)',
            '1.1.2(2)': '1.1.2(2)',
            '1.1.4': '1.1.4',
            '1.1.5(1)': '1.1.5(1)',
            '1.1.6': '1.1.6',
            '1.1.7(1)': '1.1.7(1)',
            '1.1.7(2)': '1.1.7(2)',
            '1.1.8': '1.1.8',
            '1.1.12': '1.1.12',
            '1.1.14(2)': '1.1.14(2)',
            '1.2.1(6)': '1.2.1(6)',
            '1.2.2': '1.2.2',
            '1.2.3(1)': '1.2.3(1)',
            '1.2.3(3)': '1.2.3(3)',
            '2.1': '2.1',
            '2.3.1': '2.3.1',
            '2.6': '2.6',
        }

        # Regex patterns for number formatting
        self.number_patterns = [
            # Fix comma placement in numbers (1,234.56 -> 1,234.56)
            (r'(\d{1,3})(?:,\s*)(\d{3})(?:,\s*)(\d{3})', r'\1,\2,\3'),
            (r'(\d{1,3})(?:,\s*)(\d{3})', r'\1,\2'),

            # Fix decimal places (123.4 -> 123.40, 123 -> 123.00)
            (r'(\d+,\d{3})\.(\d)$', r'\1.0\2'),
            (r'(\d+)\.(\d)$', r'\1.0\2'),
            (r'(\d+)$', r'\1.00'),

            # Remove extra spaces in numbers
            (r'(\d)\s*,\s*(\d)', r'\1,\2'),
            (r'(\d)\s*\.\s*(\d)', r'\1.\2'),
        ]

        # Field-specific patterns
        self.field_patterns = {
            'hn': re.compile(r'HN\s*[:\-]?\s*(\d+)', re.IGNORECASE),
            'an': re.compile(r'AN\s*[:\-]?\s*(\d+)', re.IGNORECASE),
            'receipt_no': re.compile(r'Receipt\s+(?:Number|Numbel|Numoer)\s*[:\-]?\s*(\d+)', re.IGNORECASE),
            'date': re.compile(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})'),
        }

    def correct_ocr_text(self, ocr_text: str) -> str:
        """
        แก้ไขข้อผิดพลาดใน OCR text โดยรวม

        Args:
            ocr_text: ข้อความจาก OCR

        Returns:
            ข้อความที่แก้ไขแล้ว
        """
        if not ocr_text:
            return ocr_text

        logger.info(f"Starting OCR correction on {len(ocr_text)} characters")

        original_text = ocr_text

        # 1. Character-level corrections
        ocr_text = self._correct_characters(ocr_text)

        # 2. Number formatting corrections
        ocr_text = self._correct_number_formatting(ocr_text)

        # 3. Medical term corrections
        ocr_text = self._correct_medical_terms(ocr_text)

        # 4. Field-specific corrections
        ocr_text = self._correct_field_specific(ocr_text)

        # 5. Clean up artifacts
        ocr_text = self._cleanup_artifacts(ocr_text)

        corrected_chars = sum(1 for a, b in zip(original_text, ocr_text) if a != b)
        logger.info(f"OCR correction completed: {corrected_chars} characters changed")

        return ocr_text

    def _correct_characters(self, text: str) -> str:
        """แก้ไขตัวอักษรที่ OCR อ่านผิด"""
        corrected = text

        # Apply character corrections
        for wrong, correct in self.char_corrections.items():
            corrected = corrected.replace(wrong, correct)

        return corrected

    def _correct_number_formatting(self, text: str) -> str:
        """แก้ไขรูปแบบตัวเลข"""
        corrected = text

        # Apply number formatting patterns
        for pattern, replacement in self.number_patterns:
            corrected = re.sub(pattern, replacement, corrected)

        # Fix common OCR number errors in context
        # e.g., "1.1.1 (1)" -> "1.1.1(1)"
        corrected = re.sub(r'(\d+\.\d+(?:\.\d+)?)\s*\(\s*(\d+)\s*\)', r'\1(\2)', corrected)

        # Fix spacing in billing amounts: "1,234 . 56" -> "1,234.56"
        corrected = re.sub(r'(\d{1,3}(?:,\d{3})*)\s*\.\s*(\d{2})', r'\1.\2', corrected)

        return corrected

    def _correct_medical_terms(self, text: str) -> str:
        """แก้ไขคำศัพท์ทางการแพทย์และเรียกเก็บเงิน"""
        corrected = text

        # Common medical billing terms corrections
        medical_corrections = {
            'ค่าตรวจ Lab': 'ค่าตรวจ Lab',
            'ค่าตรวจวินิจฉัยโดยวิธีพิเศษ': 'ค่าตรวจวินิจฉัยโดยวิธีพิเศษ',
            'ค่าอุปกรณ์ของใช้และเครื่องมือที่ใช้นอกห้องผ่าตัด': 'ค่าอุปกรณ์ของใช้และเครื่องมือที่ใช้นอกห้องผ่าตัด',
            'ค่าอุปกรณ์และเครื่องมือที่ใช้ในห้องผ่าตัด': 'ค่าอุปกรณ์และเครื่องมือที่ใช้ในห้องผ่าตัด',
            'ค่าห้องผ่าตัดและห้องคลอด': 'ค่าห้องผ่าตัดและห้องคลอด',
            'ค่าบริการการพยาบาล': 'ค่าบริการการพยาบาล',
            'ค่าบริการทางการแพทย์อื่นๆ': 'ค่าบริการทางการแพทย์อื่นๆ',
            'ค่าตรวจรักษาผู้ป่วยใน': 'ค่าตรวจรักษาผู้ป่วยใน',
            'ค่าทำศัลยกรรมและหัตถการต่างๆ': 'ค่าทำศัลยกรรมและหัตถการต่างๆ',
            'ค่าวิสัญญีแพทย์ และ/หรือ วิสัญญีพยาบาล': 'ค่าวิสัญญีแพทย์ และ/หรือ วิสัญญีพยาบาล',
            'ค่าผู้ประกอบวิชาชีพพยาบาลและผดุงครรภ์': 'ค่าผู้ประกอบวิชาชีพพยาบาลและผดุงครรภ์',
            'ค่าห้องหรือค่าเตียงผู้ป่วยใน ประเภทต่างๆ': 'ค่าห้องหรือค่าเตียงผู้ป่วยใน ประเภทต่างๆ',
            'อาหารผู้ป่วยในปกติ': 'อาหารผู้ป่วยในปกติ',
            'ค่าบริการอื่นๆ': 'ค่าบริการอื่นๆ',
        }

        for wrong, correct in medical_corrections.items():
            corrected = corrected.replace(wrong, correct)

        return corrected

    def _correct_field_specific(self, text: str) -> str:
        """แก้ไขข้อมูลในแต่ละฟิลด์โดยเฉพาะ"""
        corrected = text

        # Fix date formats
        corrected = re.sub(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', r'\1/\2/\3', corrected)

        # Fix time formats
        corrected = re.sub(r'(\d{1,2}):(\d{2}):(\d{2})', r'\1:\2:\3', corrected)

        # Fix HN/AN formats
        corrected = re.sub(r'HN\s*[:\-]?\s*(\d+)', r'HN \1', corrected)
        corrected = re.sub(r'AN\s*[:\-]?\s*(\d+)', r'AN \1', corrected)

        return corrected

    def _cleanup_artifacts(self, text: str) -> str:
        """ล้างข้อมูลที่ไม่ต้องการออก"""
        corrected = text

        # Remove multiple spaces
        corrected = re.sub(r'\s+', ' ', corrected)

        # Fix line breaks in the middle of billing items
        # This helps with OCR that breaks lines incorrectly
        lines = corrected.split('\n')
        cleaned_lines = []

        for i, line in enumerate(lines):
            # If line ends with a number and next line starts with number or description,
            # they might be part of the same billing item
            if (i < len(lines) - 1 and
                re.search(r'\d+\.\d+$', line.strip()) and
                (lines[i+1].strip().startswith(('1.', '2.', '3.')) or
                 re.search(r'^\d+\.\d+', lines[i+1].strip()))):
                # Merge lines
                merged = line.strip() + ' ' + lines[i+1].strip()
                cleaned_lines.append(merged)
                # Skip next line as it's merged
                lines[i+1] = ''
            elif line.strip():
                cleaned_lines.append(line)

        corrected = '\n'.join(cleaned_lines)

        return corrected

    def validate_corrections(self, original: str, corrected: str) -> Dict[str, Any]:
        """
        ตรวจสอบความถูกต้องของการแก้ไข

        Returns:
            Dict with validation metrics
        """
        changes = []
        for i, (orig_char, corr_char) in enumerate(zip(original, corrected)):
            if orig_char != corr_char:
                changes.append({
                    'position': i,
                    'original': orig_char,
                    'corrected': corr_char,
                    'context': original[max(0, i-10):min(len(original), i+11)]
                })

        return {
            'total_changes': len(changes),
            'change_details': changes[:20],  # First 20 changes
            'correction_confidence': min(95.0, 100.0 - (len(changes) * 0.1))
        }

    def get_correction_stats(self, ocr_text: str) -> Dict[str, int]:
        """วิเคราะห์สถิติของข้อผิดพลาด OCR ที่พบ"""
        stats = defaultdict(int)

        # Count potential issues
        lines = ocr_text.split('\n')
        for line in lines:
            # Check for common OCR error patterns
            if re.search(r'\d{1,3}\s*\.\s*\d{1,3}\s*\.\s*\d{1,3}', line):
                stats['potential_billing_codes'] += 1

            if re.search(r'\d{1,3}(?:,\d{3})*\.\d{1,2}', line):
                stats['potential_amounts'] += 1

            # Check for garbled characters
            if re.search(r'[^\w\s\.,\-\(\)\/:฿]', line):
                stats['special_characters'] += 1

        stats['total_lines'] = len(lines)
        stats['total_chars'] = len(ocr_text)

        return dict(stats)


# Singleton instance for easy access
_correction_manager = None

def get_correction_manager() -> OCRCorrectionManager:
    """Get singleton instance of OCR correction manager"""
    global _correction_manager
    if _correction_manager is None:
        _correction_manager = OCRCorrectionManager()
    return _correction_manager


def correct_ocr_text(ocr_text: str) -> str:
    """
    Convenience function to correct OCR text

    Args:
        ocr_text: Original OCR text

    Returns:
        Corrected OCR text
    """
    manager = get_correction_manager()
    return manager.correct_ocr_text(ocr_text)


def validate_ocr_corrections(original: str, corrected: str) -> Dict[str, Any]:
    """
    Validate OCR corrections

    Args:
        original: Original OCR text
        corrected: Corrected OCR text

    Returns:
        Validation results
    """
    manager = get_correction_manager()
    return manager.validate_corrections(original, corrected)


if __name__ == "__main__":
    # Test the correction module
    test_text = """โรงพยาบาลนครพัฒน์ ดูขวาง ต.ในเมือง อ.เมือง จ.นครศรีธรรมราช
ใบแจงยอดค่ารักษาพยาบาล ชื่อ Name นางสาวธรรศจรส บุญไกร
HN 0252556 AN 650000009
วันที่5/1/2565 12:44:17
1.1.1(1) ยาผู้ป่วยใน 17,313 . 00 865 . 00 16,448 . 00
1.1.1(2) ยาผู้ป่วยกลมบ 6,181.00 0.00 36,181.00"""

    manager = get_correction_manager()
    corrected = manager.correct_ocr_text(test_text)

    print("Original:")
    print(repr(test_text))
    print("\nCorrected:")
    print(repr(corrected))

    validation = manager.validate_corrections(test_text, corrected)
    print(f"\nValidation: {validation['total_changes']} changes, confidence: {validation['correction_confidence']:.1f}%")
