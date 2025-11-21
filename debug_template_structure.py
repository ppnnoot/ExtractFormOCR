#!/usr/bin/env python3

import json
from template_api_manager import TemplateAPIManager

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize manager
manager = TemplateAPIManager(config)

# Get template
template_config = manager.get_template('medical_receipt')

if template_config:
    print("Template config structure:")
    print(json.dumps(template_config, indent=2))
    print("\nKeys in template_config:")
    for key in template_config.keys():
        print(f"  - {key}")
    
    # Check for Template_json specifically
    if 'Template_json' in template_config:
        print("\nTemplate_json found!")
        template_json = template_config['Template_json']
        if isinstance(template_json, str):
            try:
                parsed_template = json.loads(template_json)
                print("Template_json structure:")
                print(json.dumps(parsed_template, indent=2))
            except json.JSONDecodeError as e:
                print(f"Failed to parse Template_json: {e}")
        else:
            print("Template_json is already parsed:")
            print(json.dumps(template_json, indent=2))
    else:
        print("\nTemplate_json NOT found in template_config")
else:
    print("Template not found")