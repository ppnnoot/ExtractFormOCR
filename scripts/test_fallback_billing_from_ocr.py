import sys
import os
from typing import Any, Dict

# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.append(ROOT)

from ai_simple_extraction import SimpleAIExtractor


class FakeResponse:
    def __init__(self, content: str):
        self.status_code = 200
        self._content = content

    def json(self) -> Dict[str, Any]:
        return {
            "choices": [
                {"message": {"content": self._content}}
            ]
        }

    @property
    def text(self) -> str:
        return self._content


def main():
    # Prepare OCR that includes pipe-delimited billing lines
    ocr_results = [
        {"text": "HOSPITAL_NAME: โรงพยาบาลนครพัฒน์"},
        {"text": "BILLING_ITEMS:"},
        {"text": "1.1 | ค่าห้องพิเศษ | 2,000.00 | 0.00 | 2,000.00"},
        {"text": "1.2 | ค่าบริการพยาบาล | 500.00 | 0.00 | 500.00"},
        {"text": "2 | ค่ายา | 1,200.00 | 100.00 | 1,100.00"},
    ]

    # Minimal config with dummy endpoint
    config = {
        "ai_extraction": {
            "api": {
                "endpoint": "http://dummy",
                "model": "stub-model",
                "temperature": 0.0,
                "top_p": 0.8,
                "max_tokens": 512,
                "frequency_penalty": 0,
                "presence_penalty": 0,
                "timeout": 5,
                "max_retries": 1,
            },
            "prompt_optimization": {"max_ocr_results": 200},
        },
        "templates": {"default": "medical_receipt", "form_id_mapping": {}},
    }

    extractor = SimpleAIExtractor(config)

    # Monkeypatch requests.post to return content with no billing items
    import ai_simple_extraction as mod
    import types

    def fake_post(url, headers=None, json=None, timeout=None):
        # Return content missing BILLING_ITEMS lines so fallback is invoked
        content = "HOSPITAL_NAME: โรงพยาบาลนครพัฒน์\nHN: 0252556\n"
        return FakeResponse(content)

    # Patch inside function scope
    import requests as real_requests
    original_post = real_requests.post
    try:
        real_requests.post = fake_post  # type: ignore
        result = extractor.extract_simple(ocr_results, template="medical_receipt")
    finally:
        real_requests.post = original_post

    # Print summary
    billing = result.get("billing_items", [])
    print(f"Parsed billing_items: {len(billing)}")
    for i, it in enumerate(billing[:3], 1):
        print(f"{i}. code={it.get('code')} desc={it.get('desc')} net={it.get('net_amount')}")
    print(f"gross_amount: {result.get('gross_amount')}")


if __name__ == "__main__":
    main()