import json
from pathlib import Path
import sys

# Ensure project root is on sys.path for import
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from ai_simple_extraction import JSONFormatter


def build_minimal_template():
    return {
        "form_id": "HL0000000",
        "document_type": "Medical Receipt",
        "Template_json": {
            "documents": [
                {
                    "document_code": "HL0000000",
                    "document_type": "Medical Receipt",
                    "page": "1",
                    "total_page": "1",
                    "document_info": [
                        {"accuracyRate": None, "type": "string", "code": "vn", "value": None, "page": None},
                        {"accuracyRate": None, "type": "string", "code": "receipt_no", "value": None, "page": None},
                        {"accuracyRate": None, "type": "date", "code": "receipt_date", "value": None, "page": None},
                        {"accuracyRate": None, "type": "integer", "code": "age", "value": None, "page": None},
                    ]
                }
            ],
            "metadata": {}
        }
    }


def main():
    simple_data = {
        # Only vn present, others missing
        "vn": "VN123",
        "receipt_no": None,
        "receipt_date": None,
        "age": None,
    }

    template_config = build_minimal_template()
    formatted = JSONFormatter.format_to_medical_receipt_json(
        simple_data,
        metadata={"test": True},
        template_config=template_config,
    )

    docs = formatted.get("documents", [])
    if not docs:
        print("[ERROR] No documents in formatted output")
        return 1

    doc_info = docs[0].get("document_info", [])
    # Index by code for easy checks
    idx = {f.get("code"): f for f in doc_info}

    def show(code):
        f = idx.get(code)
        print(f"{code}: value={json.dumps(f.get('value'))}, accuracyRate={json.dumps(f.get('accuracyRate'))}")

    print("[RESULT] Field values after formatting and normalization:")
    for code in ["vn", "receipt_no", "receipt_date", "age"]:
        show(code)

    # Assertions: missing ones must be null (None)
    vn_ok = idx["vn"].get("value") == "VN123"
    rn_null = idx["receipt_no"].get("value") is None
    rd_null = idx["receipt_date"].get("value") is None
    age_null = idx["age"].get("value") is None

    if vn_ok and rn_null and rd_null and age_null:
        print("[SUCCESS] Missing values are NULL, present value remains set.")
        return 0
    else:
        print("[FAIL] Expected NULLs for missing fields.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())