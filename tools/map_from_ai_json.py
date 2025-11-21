#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Map extracted_content (with [L1]/[L2]/[L3]) from AI JSON -> billing_items (L1+L2) and order_items (L3).
Usage:
  python tools/map_from_ai_json.py output/ai_debug/responses/response_20251116_175215_b5d9d090.json

Outputs:
  - Writes mapped JSON to: output/mapped/<same_basename>.mapped.json
  - Prints counts and a small sample to stdout
"""
import sys
import json
import re
from pathlib import Path


def parse_hierarchical(text: str):
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    billing_items = []  # L1 list
    current_l1 = None
    current_l2 = None
    l3_count = 0

    for line in lines:
        s = line.strip()
        if not s:
            continue

        if s.startswith('[L1]'):
            clean = s[4:].strip()
            parts = [p.strip() for p in clean.split('|')]
            if len(parts) >= 5:
                import re as _re
                first = parts[0]
                is_amount_first = bool(_re.match(r'^\d+(?:\.\d+)?$', first.replace(',', '')))
                if is_amount_first:
                    item = {
                        'billing_code': '-',
                        'billing_desc': parts[1],
                        'amount': parts[2],
                        'discount': parts[3],
                        'net_amount': parts[4],
                        'item_level': 1,
                        'grouporder_items': []
                    }
                else:
                    item = {
                        'billing_code': parts[0],
                        'billing_desc': parts[1],
                        'amount': parts[2],
                        'discount': parts[3],
                        'net_amount': parts[4],
                        'item_level': 1,
                        'grouporder_items': []
                    }
                billing_items.append(item)
                current_l1 = item
                current_l2 = None
            continue

        if s.startswith('[L2]'):
            clean = s[4:].strip()
            parts = [p.strip() for p in clean.split('|')]
            if len(parts) >= 5:
                import re as _re
                first = parts[0]
                is_amount_first = bool(_re.match(r'^\d+(?:\.\d+)?$', first.replace(',', '')))
                if is_amount_first:
                    item = {
                        'billing_code': '-',
                        'billing_desc': parts[1],
                        'amount': parts[2],
                        'discount': parts[3],
                        'net_amount': parts[4],
                        'item_level': 2,
                        'order_items': []
                    }
                else:
                    item = {
                        'billing_code': parts[0],
                        'billing_desc': parts[1],
                        'amount': parts[2],
                        'discount': parts[3],
                        'net_amount': parts[4],
                        'item_level': 2,
                        'order_items': []
                    }
                # Ensure L1 parent exists (create wrapper if needed)
                if current_l1 is None:
                    prefix = item['billing_code'].split('.')[0] if item['billing_code'] and item['billing_code'] != '-' else '1'
                    l1_wrap = {
                        'billing_code': f"{prefix}.",
                        'billing_desc': item['billing_desc'],
                        'amount': item['amount'],
                        'discount': item['discount'],
                        'net_amount': item['net_amount'],
                        'item_level': 1,
                        'grouporder_items': []
                    }
                    billing_items.append(l1_wrap)
                    current_l1 = l1_wrap
                current_l1['grouporder_items'].append(item)
                current_l2 = item
            continue

        if s.startswith('[L3]'):
            clean = s[4:].strip()
            parts = [p.strip() for p in clean.split('|')]
            item = None
            if len(parts) >= 5:
                # Regular 5-part L3
                item = {
                    'billing_desc': parts[0],
                    'quantity': parts[1],
                    'amount': parts[2],
                    'discount': parts[3],
                    'net_amount': parts[4],
                    'item_level': 3
                }
            elif len(parts) == 4:
                # Heuristic 4-part L3:
                # A) item | quantity | amount | net (missing discount)
                # B) item | amount | discount | net (missing quantity)
                m = re.sub(r'[ ,]', '', parts[1] or '')
                is_num = bool(re.match(r'^\d+(?:\.\d+)?$', m))
                if is_num:
                    # quantity missing
                    item = {
                        'billing_desc': parts[0],
                        'quantity': '1',
                        'amount': parts[1],
                        'discount': parts[2],
                        'net_amount': parts[3],
                        'item_level': 3
                    }
                else:
                    # discount missing
                    item = {
                        'billing_desc': parts[0],
                        'quantity': parts[1],
                        'amount': parts[2],
                        'discount': '0.00',
                        'net_amount': parts[3],
                        'item_level': 3
                    }
            if item is None:
                continue

            # Ensure L2 parent exists (create dummy if needed)
            if current_l2 is None:
                if current_l1 is None:
                    # Cannot place this L3 without any parent context
                    continue
                dummy = {
                    'billing_code': f"{current_l1['billing_code']}1",
                    'billing_desc': current_l1['billing_desc'],
                    'amount': '0.00',
                    'discount': '0.00',
                    'net_amount': '0.00',
                    'item_level': 2,
                    'order_items': []
                }
                current_l1['grouporder_items'].append(dummy)
                current_l2 = dummy

            current_l2['order_items'].append(item)
            l3_count += 1
            continue

    return billing_items, l3_count


def build_flat_arrays(billing_items):
    billing_flat = []
    order_flat = []

    # Map: L2 code -> sequential item_no (1-based across billing_flat)
    code_to_seq = {}
    seq = 0

    for l1 in billing_items:
        seq += 1
        code_to_seq[l1['billing_code']] = str(seq)
        billing_flat.append({
            'item_no': l1['billing_code'],
            'billing_desc': l1['billing_desc'],
            'amount': l1.get('amount'),
            'discount': l1.get('discount'),
            'net_amount': l1.get('net_amount'),
            'item_level': 1
        })
        for l2 in l1.get('grouporder_items', []):
            seq += 1
            code_to_seq[l2['billing_code']] = str(seq)
            billing_flat.append({
                'item_no': l2['billing_code'],
                'billing_desc': l2['billing_desc'],
                'amount': l2.get('amount'),
                'discount': l2.get('discount'),
                'net_amount': l2.get('net_amount'),
                'item_level': 2
            })

    for l1 in billing_items:
        for l2 in l1.get('grouporder_items', []):
            parent_no = code_to_seq.get(l2['billing_code'], '-')
            for l3 in l2.get('order_items', []):
                order_flat.append({
                    # item_id: keep only real IDs; if none, set "-"
                    'item_id': '-',
                    'item_desc': l3['billing_desc'],
                    'item_amont': l3.get('quantity') or '-',
                    'amount': l3.get('amount'),
                    'discount': l3.get('discount'),
                    'net_amount': l3.get('net_amount'),
                    'billing_item_no': parent_no,
                    'item_level': 3
                })

    return billing_flat, order_flat


def main():
    if len(sys.argv) < 2:
        print('Usage: python tools/map_from_ai_json.py <ai_json_path>')
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f'File not found: {src}')
        sys.exit(2)

    data = json.loads(src.read_text(encoding='utf-8'))
    text = data.get('extracted_content') or data.get('full_response', {}).get('choices', [{}])[0].get('message', {}).get('content', '')

    billing_items, l3_count = parse_hierarchical(text)
    billing_flat, order_flat = build_flat_arrays(billing_items)

    mapped = {
        'billing_items': billing_flat,
        'order_items': order_flat
    }

    out_dir = Path('output/mapped')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (src.stem + '.mapped.json')
    out_path.write_text(json.dumps(mapped, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f'Billing_items (L1+L2): {len(billing_flat)}')
    print(f'Order_items (L3): {len(order_flat)} (expected from text: {l3_count})')
    print('Sample order_items (first 3):')
    for it in order_flat[:3]:
        print(f"  - {it['item_desc'][:40]} (parent billing_item_no: {it['billing_item_no']})")
    print(f'Output saved to: {out_path}')


if __name__ == '__main__':
    main()


