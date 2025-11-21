import json
import sys
from pathlib import Path

# Ensure project root is in sys.path when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from ai_simple_extraction import SimpleAIExtractor
except Exception as e:
    print(f"Failed to import ai_simple_extraction: {e}")
    sys.exit(1)

def main(path_str: str):
    path = Path(path_str)
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)
    with path.open('r', encoding='utf-8') as f:
        doc = json.load(f)
    content = doc.get('extracted_content', '')
    extractor = SimpleAIExtractor(config={'logging': {'level': 'INFO'}, 'ai': {'endpoint': 'http://localhost'}})
    parsed = extractor._parse_simple_response(content)
    print('hospital_name:', parsed.get('hospital_name'))
    print('hn:', parsed.get('hn'))
    print('an:', parsed.get('an'))
    print('admission_date:', parsed.get('admission_date'))
    print('gross_amount:', parsed.get('gross_amount'))
    print('invoice_no:', parsed.get('invoice_no'))
    print('date_of_issue:', parsed.get('date_of_issue'))
    print('items:', len(parsed.get('billing_items', [])))

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_parse_saved_response.py <path-to-response.json>')
        sys.exit(1)
    main(sys.argv[1])