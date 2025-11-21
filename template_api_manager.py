"""
Template API Manager - Load templates from remote API with caching and security
ดึง template configuration จาก API แทนไฟล์ JSON เพื่อความยืดหยุ่น
"""

import json
import logging
import requests
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from security_module import SecurityValidator, SecurityLogger

logger = logging.getLogger(__name__)


class TemplateCache:
    """Cache manager for templates"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        
    def get(self, form_id: str) -> Optional[Dict[str, Any]]:
        """Get template from cache if not expired"""
        if form_id in self.cache:
            entry = self.cache[form_id]
            if datetime.now() < entry['expires_at']:
                logger.debug(f"Cache hit for formId: {form_id}")
                return entry['data']
            else:
                logger.debug(f"Cache expired for formId: {form_id}")
                del self.cache[form_id]
        return None
    
    def set(self, form_id: str, data: Dict[str, Any]):
        """Store template in cache"""
        self.cache[form_id] = {
            'data': data,
            'expires_at': datetime.now() + self.ttl,
            'cached_at': datetime.now()
        }
        logger.debug(f"Cached template for formId: {form_id}")
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        logger.info("Template cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            'total_cached': len(self.cache),
            'cached_forms': list(self.cache.keys())
        }


class TemplateAPIManager:
    """
    Manage templates from remote API with security, caching, and fallback
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.template_config = config.get('templates', {})
        
        # API configuration
        self.api_config = self.template_config.get('api', {})
        self.api_url = self.api_config.get('url', 'https://ocr.rg.in.th/uapi/api/KOConfiguration-GetFormId')
        # Sanitize URL: strip spaces and trailing punctuation that may cause 404 (e.g., trailing comma)
        if isinstance(self.api_url, str):
            self.api_url = self.api_url.strip().rstrip(',')
        self.api_timeout = self.api_config.get('timeout', 30)
        self.api_max_retries = self.api_config.get('max_retries', 3)
        
        # Cache configuration
        self.cache_enabled = self.template_config.get('cache_enabled', True)
        self.cache_ttl = self.template_config.get('cache_ttl', 60)  # minutes
        self.cache = TemplateCache(self.cache_ttl) if self.cache_enabled else None
        
        # Fallback to local files
        self.fallback_enabled = self.template_config.get('fallback_enabled', True)
        self.fallback_directory = self.template_config.get('directory', './templates')
        
        # Statistics
        self.stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'api_errors': 0,
            'fallback_uses': 0
        }
        
        logger.info(f"TemplateAPIManager initialized (API: {self.api_url}, Cache: {self.cache_enabled})")
    
    def get_template(self, form_id: str) -> Optional[Dict[str, Any]]:
        """
        Get template by Form ID (tries cache -> API -> fallback)
        
        Args:
            form_id: Form ID (e.g., 'HL0000050', 'HL0000052')
        
        Returns:
            Template configuration dict or None if not found
        """
        try:
            logger.info(f"Getting template for Form ID: {form_id}")
            
            # Try cache first
            if self.cache_enabled:
                cached_template = self.cache.get(form_id)
                if cached_template:
                    self.stats['cache_hits'] += 1
                    logger.info(f"Template loaded from cache: {form_id}")
                    return cached_template
                else:
                    self.stats['cache_misses'] += 1
            
            # Try API
            template = self._fetch_from_api(form_id)
            
            if template:
                # Store in cache
                if self.cache_enabled:
                    self.cache.set(form_id, template)
                return template
            
            # Fallback to local file
            if self.fallback_enabled:
                logger.warning(f"API failed, trying fallback for Form ID: {form_id}")
                return self._load_from_fallback(form_id)
            
            logger.error(f"Template not found for Form ID: {form_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting template {form_id}: {e}", exc_info=True)
            if self.fallback_enabled:
                return self._load_from_fallback(form_id)
            return None
    
    def _fetch_from_api(self, form_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch template from remote API with security validation
        
        Args:
            form_id: Form ID to fetch
        
        Returns:
            Parsed template dict or None
        """
        for attempt in range(self.api_max_retries):
            try:
                logger.info(f"Fetching template from API: {form_id} (attempt {attempt + 1}/{self.api_max_retries})")
                
                # Prepare request
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'ExtractForm-TemplateManager/1.0'
                }
                
                # POST request (as specified by user)
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json={},  # Empty body as per API spec
                    timeout=self.api_timeout
                )
                
                self.stats['api_calls'] += 1
                
                # Check response
                if response.status_code != 200:
                    logger.warning(f"API returned status {response.status_code}")
                    continue
                
                # Parse response
                data = response.json()
                
                # Validate response structure
                if not self._validate_api_response(data):
                    logger.error("Invalid API response structure")
                    self.stats['api_errors'] += 1
                    continue
                
                # Check success flag
                if not data.get('Successful', False):
                    logger.error(f"API returned error: {data.get('Message', 'Unknown error')}")
                    self.stats['api_errors'] += 1
                    continue
                
                # Find template by form_id
                template_data = self._find_template_by_form_id(data.get('data', []), form_id)
                
                if template_data:
                    logger.info(f"Template fetched successfully: {form_id}")
                    
                    # Log security event
                    SecurityLogger.log_security_event(
                        "TEMPLATE_API_SUCCESS",
                        "system",
                        {
                            'form_id': form_id,
                            'doc_name': template_data.get('docName'),
                            'attempt': attempt + 1
                        }
                    )
                    
                    return template_data
                else:
                    logger.warning(f"Template not found in API response: {form_id}")
                    continue
                    
            except requests.exceptions.Timeout:
                logger.error(f"API timeout (attempt {attempt + 1})")
                self.stats['api_errors'] += 1
                
            except requests.exceptions.ConnectionError:
                logger.error(f"API connection error (attempt {attempt + 1})")
                self.stats['api_errors'] += 1
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response: {e}")
                self.stats['api_errors'] += 1
                
            except Exception as e:
                logger.error(f"Unexpected error fetching template: {e}", exc_info=True)
                self.stats['api_errors'] += 1
        
        # All attempts failed
        logger.error(f"Failed to fetch template after {self.api_max_retries} attempts")
        
        # Log security event
        SecurityLogger.log_security_event(
            "TEMPLATE_API_FAILURE",
            "system",
            {
                'form_id': form_id,
                'attempts': self.api_max_retries
            }
        )
        
        return None
    
    def _validate_api_response(self, data: Dict[str, Any]) -> bool:
        """
        Validate API response structure
        
        Args:
            data: API response data
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['Successful', 'Code', 'Message', 'data']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field in API response: {field}")
                return False
        
        if not isinstance(data['data'], list):
            logger.error("API response 'data' must be a list")
            return False
        
        return True
    
    def _find_template_by_form_id(self, templates: List[Dict[str, Any]], form_id: str) -> Optional[Dict[str, Any]]:
        """
        Find template in list by formId and parse Template_json
        
        Args:
            templates: List of template dicts from API
            form_id: Form ID to find
        
        Returns:
            Parsed template dict or None
        """
        for template in templates:
            if template.get('formId') == form_id:
                # Parse Template_json string
                template_json_str = template.get('Template_json', '{}')
                
                try:
                    # Parse JSON string
                    template_json = json.loads(template_json_str)
                    
                    # Combine with metadata
                    result = {
                        'form_id': template.get('formId'),
                        'document_type': template.get('docName'),
                        'document_type_thai': template.get('docThaiName'),
                        'description': template.get('docType'),
                        'category': template.get('docCat'),
                        'subcategory': template.get('docSubCat'),
                        'is_extraction': template.get('isExtraction', 0) == 1,
                        'template_structure': template_json,
                        'metadata': {
                            'id': template.get('Id'),
                            'class': template.get('class'),
                            'func_group': template.get('funcGroup'),
                            'update_date': template.get('UpdateDate'),
                            'sequence': template.get('sequence')
                        }
                    }
                    
                    logger.debug(f"Parsed template: {form_id} - {result['document_type']}")
                    return result
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Template_json for {form_id}: {e}")
                    return None
        
        return None
    
    def _load_from_fallback(self, form_id: str) -> Optional[Dict[str, Any]]:
        """
        Load template from local fallback file
        
        Args:
            form_id: Form ID
        
        Returns:
            Template dict or None
        """
        try:
            self.stats['fallback_uses'] += 1
            
            # Try file with Form ID name
            file_path = Path(self.fallback_directory) / f"{form_id}.json"
            
            if file_path.exists():
                logger.info(f"Loading template from fallback: {file_path}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Wrap in standard format
                return {
                    'form_id': form_id,
                    'document_type': data.get('document_type', form_id),
                    'description': data.get('description', ''),
                    'template_structure': data.get('output_format', data),
                    'source': 'fallback_file',
                    'metadata': {
                        'file_path': str(file_path)
                    }
                }
            
            logger.error(f"No fallback file found for Form ID: {form_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading fallback template {form_id}: {e}", exc_info=True)
            return None
    
    def get_all_templates(self) -> List[Dict[str, Any]]:
        """
        Get all available templates from API
        
        Returns:
            List of all templates
        """
        try:
            logger.info("Fetching all templates from API")
            
            response = requests.post(
                self.api_url,
                headers={'Content-Type': 'application/json'},
                json={},
                timeout=self.api_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('Successful') and 'data' in data:
                    templates = []
                    
                    for template_data in data['data']:
                        parsed = self._find_template_by_form_id(
                            [template_data],
                            template_data.get('formId')
                        )
                        if parsed:
                            templates.append(parsed)
                    
                    logger.info(f"Fetched {len(templates)} templates from API")
                    return templates
            
            logger.error("Failed to fetch all templates")
            return []
            
        except Exception as e:
            logger.error(f"Error fetching all templates: {e}", exc_info=True)
            return []
    
    def refresh_cache(self, form_id: Optional[str] = None):
        """
        Refresh cache for specific template or all templates
        
        Args:
            form_id: Specific form ID to refresh, or None for all
        """
        if form_id:
            logger.info(f"Refreshing cache for: {form_id}")
            template = self._fetch_from_api(form_id)
            if template and self.cache_enabled:
                self.cache.set(form_id, template)
        else:
            logger.info("Refreshing entire cache")
            if self.cache_enabled:
                self.cache.clear()
            
            # Fetch all templates
            templates = self.get_all_templates()
            
            if self.cache_enabled:
                for template in templates:
                    self.cache.set(template['form_id'], template)
            
            logger.info(f"Cache refreshed with {len(templates)} templates")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get manager statistics"""
        stats = self.stats.copy()
        
        if self.cache_enabled:
            stats['cache'] = self.cache.get_stats()
        
        return stats
    
    def get_available_form_ids(self) -> List[str]:
        """Get list of available Form IDs from API"""
        try:
            templates = self.get_all_templates()
            return [t['form_id'] for t in templates if 'form_id' in t]
        except:
            return []


# Test function
def test_template_api_manager():
    """Test the Template API Manager"""
    
    # Test configuration
    config = {
        'templates': {
            'api': {
                'url': 'https://ocr.rg.in.th/uapi/api/KOConfiguration-GetFormId',
                'timeout': 30,
                'max_retries': 3
            },
            'cache_enabled': True,
            'cache_ttl': 60,
            'fallback_enabled': True,
            'directory': './templates'
        }
    }
    
    # Initialize manager
    manager = TemplateAPIManager(config)
    
    print("\n=== Template API Manager Test ===\n")
    
    # Test 1: Get single template by Form ID
    print("Test 1: Get template for HL0000050")
    template = manager.get_template('HL0000050')
    
    if template:
        print(f"[OK] Template loaded: {template['document_type']}")
        print(f"   Form ID: {template['form_id']}")
        print(f"   Description: {template['description']}")
        print(f"   Has structure: {bool(template.get('template_structure'))}")
    else:
        print("[FAIL] Failed to load template")
    
    # Test 2: Cache hit
    print("\nTest 2: Get same template (should use cache)")
    template2 = manager.get_template('HL0000050')
    
    if template2:
        print(f"[OK] Template loaded from cache")
    
    # Test 3: Get all templates
    print("\nTest 3: Get all templates")
    all_templates = manager.get_all_templates()
    print(f"[OK] Found {len(all_templates)} templates:")
    
    for t in all_templates[:5]:  # Show first 5
        print(f"   - {t['form_id']}: {t['document_type']}")
    
    # Test 4: Statistics
    print("\nTest 4: Statistics")
    stats = manager.get_statistics()
    print(f"[OK] Statistics:")
    print(f"   API Calls: {stats['api_calls']}")
    print(f"   Cache Hits: {stats['cache_hits']}")
    print(f"   Cache Misses: {stats['cache_misses']}")
    print(f"   API Errors: {stats['api_errors']}")
    print(f"   Fallback Uses: {stats['fallback_uses']}")
    
    if 'cache' in stats:
        print(f"   Cached Templates: {stats['cache']['total_cached']}")
    
    print("\n=== Test Complete ===\n")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run test
    test_template_api_manager()

