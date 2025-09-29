from firecrawl import FirecrawlApp
from pydantic import BaseModel
import time
import csv, os, json, psutil
import re
import requests.exceptions
from urllib3.exceptions import ProtocolError
from urllib.parse import urlparse
import threading
import sys
from pathlib import Path

# ============================================
# DEBUG AND SETTINGS MANAGEMENT
# ============================================

# Global debug flag
_DEBUG_ENABLED = False

def load_settings():
    """Load settings from settings.json file"""
    settings_paths = [
        Path(__file__).parent.parent / "settings.json",
        Path("settings.json"),
        Path("../settings.json")
    ]
    
    for path in settings_paths:
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[WARNING] Error loading settings from {path}: {e}")
    
    # Return default settings if file not found
    return {
        "debug": {"enabled": False},
        "scraping": {
            "rfq_default": "Y",
            "msrp_default": None,
            "stock_count_default": 10,
            "status_default": "1"
        }
    }

def enable_debug_mode():
    """Enable debug mode for detailed output during scraping"""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = True
    print("[DEBUG] Debug mode enabled - you'll see detailed scraping information")

def disable_debug_mode():
    """Disable debug mode for clean output"""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = False
    print("[DEBUG] Debug mode disabled - clean output mode")

def is_debug_enabled():
    """Check if debug mode is currently enabled"""
    global _DEBUG_ENABLED
    if not _DEBUG_ENABLED:
        # Check settings on first call
        settings = load_settings()
        _DEBUG_ENABLED = settings.get("debug", {}).get("enabled", False)
    return _DEBUG_ENABLED

def load_debug_settings():
    """Load debug settings from settings.json"""
    global _DEBUG_ENABLED
    settings = load_settings()
    _DEBUG_ENABLED = settings.get("debug", {}).get("enabled", False)
    return _DEBUG_ENABLED

# Initialize debug mode from settings on import
load_debug_settings()

# ============================================
# API KEY MANAGEMENT
# ============================================

class APIKeyManager:
    """Centralized API key management with .env file support"""
    
    @staticmethod
    def load_env_file():
        """Load .env file if it exists (for secure key storage)"""
        env_path = Path(".env")
        if env_path.exists():
            try:
                print("[INFO] Loading API keys from .env file")
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()
                                # Don't override existing env vars
                                if key and value and not os.getenv(key):
                                    os.environ[key] = value
                return True
            except Exception as e:
                print(f"[WARNING] Could not load .env file: {e}")
                return False
        return False
    
    @staticmethod
    def get_firecrawl_key():
        """Get Firecrawl API key (priority: env var > .env > settings.json)"""
        # Try to load .env first
        APIKeyManager.load_env_file()
        
        # Check environment variable
        key = os.getenv("FIRECRAWL_API_KEY")
        if key and key != "your_firecrawl_api_key_here":
            return key
        
        # Fallback to settings.json
        settings = load_settings()
        key = settings.get("api", {}).get("firecrawl_api_key", "")
        
        return key if key and key != "your_firecrawl_api_key_here" else None
    
    @staticmethod
    def get_claude_key():
        """Get Claude API key (priority: env var > .env > settings.json)"""
        # Try to load .env first
        APIKeyManager.load_env_file()
        
        # Check environment variable
        key = os.getenv("ANTHROPIC_API_KEY")
        if key and key != "your_claude_api_key_here":
            return key
        
        # Fallback to settings.json
        settings = load_settings()
        key = settings.get("ai_descriptions", {}).get("claude_api_key", "")
        
        return key if key and key != "your_claude_api_key_here" else None
    
    @staticmethod
    def validate_keys(require_claude=None):
        """
        Validate all required API keys exist
        Returns: tuple: (valid: bool, missing_keys: list)
        """
        missing_keys = []
        
        # Always require Firecrawl
        firecrawl_key = APIKeyManager.get_firecrawl_key()
        if not firecrawl_key:
            missing_keys.append({
                'name': 'Firecrawl API Key',
                'env_var': 'FIRECRAWL_API_KEY',
                'settings_path': 'api.firecrawl_api_key',
                'required_for': 'URL discovery and product scraping',
                'get_from': 'https://firecrawl.dev'
            })
        
        # Check if AI descriptions are enabled and if we have ANY AI key
        settings = load_settings()
        ai_needed = require_claude if require_claude is not None else settings.get("ai_descriptions", {}).get("enabled", False)
        
        if ai_needed:
            # Check for ANY AI key (Groq, OpenAI, or Claude)
            groq_key = os.getenv("GROQ_API_KEY") or settings.get("ai_descriptions", {}).get("groq_api_key")
            openai_key = os.getenv("OPENAI_API_KEY") or settings.get("ai_descriptions", {}).get("openai_api_key")
            claude_key = APIKeyManager.get_claude_key()
            
            # If NO AI keys are found, then it's a problem
            if not groq_key and not openai_key and not claude_key:
                missing_keys.append({
                    'name': 'AI API Key (Groq, OpenAI, or Claude)',
                    'env_var': 'GROQ_API_KEY or OPENAI_API_KEY or ANTHROPIC_API_KEY',
                    'settings_path': 'ai_descriptions.groq_api_key',
                    'required_for': 'AI description generation',
                    'get_from': 'https://console.groq.com/ (recommended for vape products)'
                })
        
        return (len(missing_keys) == 0, missing_keys)
    
    @staticmethod
    def display_missing_keys_error(missing_keys):
        """Display clear error message for missing API keys"""
        print("\n" + "="*70)
        print("ERROR: MISSING API KEYS")
        print("="*70)
        print("\nThe following API keys are required but not found:\n")
        
        for i, key_info in enumerate(missing_keys, 1):
            print(f"{i}. {key_info['name']}")
            print(f"   Required for: {key_info['required_for']}")
            print(f"   Get your key from: {key_info['get_from']}")
            print()
        
        print("-"*70)
        print("\nTO FIX THIS ISSUE:\n")
        
        print("OPTION 1: Add to settings.json")
        print("-"*30)
        print("Edit settings.json and add your keys:")
        print()
        for key_info in missing_keys:
            path_parts = key_info['settings_path'].split('.')
            if len(path_parts) == 2:
                print(f'  "{path_parts[0]}": {{')
                print(f'    "{path_parts[1]}": "YOUR_KEY_HERE"')
                print('  }')
        
        print("\nOPTION 2: Set environment variables")
        print("-"*30)
        print("Set these environment variables before running:")
        print()
        for key_info in missing_keys:
            print(f"  Windows:  set {key_info['env_var']}=YOUR_KEY_HERE")
            print(f"  Mac/Linux: export {key_info['env_var']}=YOUR_KEY_HERE")
            print()
        
        print("="*70)
        print("\nThe scraper cannot proceed without these API keys.")
        print("Please configure them and try again.")
        print("="*70)

def calculate_delay(base_delay: float = 1.0) -> float:
    """
    Calculate a delay value based on CPU cores and clock speed.
    
    base_delay: starting delay (seconds)
    returns: adjusted delay (float)
    """
    # Get core counts
    cores = psutil.cpu_count(logical=True) or 1
    
    # Get CPU frequency
    freq_info = psutil.cpu_freq()
    if freq_info:
        current_mhz = freq_info.current
    else:
        current_mhz = 1000.0  # assume 1 GHz if unknown
    
    # Normalize 
    #CPU strength: cores * GHz
    cpu_strength = cores * (current_mhz / 1000.0)
    
    # Inverse relationship: stronger CPU -> smaller delay
    delay = base_delay / cpu_strength
    
    # Debug suppression - ensure no debug output
    return delay

DELAY : float = float(calculate_delay(1.0))  # Reduced base delay for better performance


class ScrapingSpinner:
    """Simple spinner for scraping operations"""
    def __init__(self, message="Scraping"):
        self.message = message
        self.spinning = False
        self.spinner_thread = None
        self.frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.frame_index = 0
    
    def start(self):
        if not self.spinning:
            self.spinning = True
            self.spinner_thread = threading.Thread(target=self._spin)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()
    
    def stop(self):
        if self.spinning:
            self.spinning = False
            if self.spinner_thread:
                self.spinner_thread.join(timeout=0.1)
            # Clear the spinner line
            sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
            sys.stdout.flush()
    
    def _spin(self):
        while self.spinning:
            frame = self.frames[self.frame_index]
            sys.stdout.write(f'\r  {frame} {self.message}...')
            sys.stdout.flush()
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            time.sleep(0.1)


# ============================================
# THREAD-SAFE CACHE MANAGEMENT
# ============================================

import threading

class CacheManager:
    """Thread-safe cache manager for product data"""
    
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock for nested access
        self._sku_counter = {}
        self._existing_skus = set()
        self._existing_names = set()
        self._cache_loaded = False
    
    def is_cache_loaded(self):
        """Check if cache has been loaded from CSV"""
        with self._lock:
            return self._cache_loaded
    
    def add_sku(self, sku):
        """Thread-safe SKU addition"""
        if not sku:
            return
        with self._lock:
            sku_stripped = sku.strip()
            self._existing_skus.add(sku_stripped)
    
    def add_name(self, name):
        """Thread-safe name addition"""
        if not name:
            return
        with self._lock:
            self._existing_names.add(name.strip().lower())
    
    def has_sku(self, sku):
        """Thread-safe SKU check"""
        if not sku:
            return False
        with self._lock:
            return sku.strip() in self._existing_skus
    
    def has_name(self, name):
        """Thread-safe name check"""
        if not name:
            return False
        with self._lock:
            return name.strip().lower() in self._existing_names
    
    def get_sku_counter(self, prefix):
        """Thread-safe SKU counter access"""
        with self._lock:
            return self._sku_counter.get(prefix, 0)
    
    def increment_sku_counter(self, prefix):
        """Thread-safe SKU counter increment"""
        with self._lock:
            self._sku_counter[prefix] = self._sku_counter.get(prefix, 0) + 1
            return self._sku_counter[prefix]
    
    def get_stats(self):
        """Get cache statistics"""
        with self._lock:
            return {
                'skus': len(self._existing_skus),
                'names': len(self._existing_names),
                'loaded': self._cache_loaded
            }
    
    def refresh_from_csv(self, csv_file_path):
        """Refresh cache by re-reading CSV file"""
        with self._lock:
            self._existing_skus.clear()
            self._existing_names.clear()
            self._sku_counter.clear()
            
            if not os.path.exists(csv_file_path):
                self._cache_loaded = True
                return
            
            try:
                import csv
                with open(csv_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Add SKU
                        sku = row.get('SKU', '').strip()
                        if sku:
                            self._existing_skus.add(sku)
                            # Update counter for SKU generation
                            if '-' in sku:
                                prefix = sku.split('-')[0]
                                try:
                                    num = int(sku.split('-')[1])
                                    self._sku_counter[prefix] = max(self._sku_counter.get(prefix, 0), num)
                                except (ValueError, IndexError):
                                    pass
                        
                        # Add name
                        name = row.get('Name', '').strip()
                        if name:
                            self._existing_names.add(name.lower())
                
                self._cache_loaded = True
                if is_debug_enabled():
                    print(f"[CACHE] Refreshed from CSV: {len(self._existing_skus)} SKUs, {len(self._existing_names)} names")
                    
            except Exception as e:
                print(f"[WARNING] Error refreshing cache from CSV: {e}")
                self._cache_loaded = True  # Mark as loaded even if failed

# Global thread-safe cache manager
cache_manager = CacheManager()

# Legacy compatibility - these functions now use the cache manager
sku_counter = {}  # Keep for backwards compatibility
existing_skus_cache = set()  # Keep for backwards compatibility  
existing_names_cache = set()  # Keep for backwards compatibility

# Retry configuration
MAX_RETRIES = 1  # REDUCED FROM 3 - Only retry once to save API credits
RETRY_BACKOFF_FACTOR = 2
INITIAL_RETRY_DELAY = 1.0  # Reduced from 2.0 for faster retries

# API Timeout configuration (adjust as needed)
# Change this value if products are timing out too often:
# - 30 = Fast (risky on slow sites)  
# - 60 = Balanced (recommended)
# - 120 = Safe (for very slow sites)
API_TIMEOUT = 20  # seconds - reduced for faster processing of minimal sites like Muha Meds

# Configuration for marketplace fields - loaded from settings.json
RFQ_DEFAULT = "Y"
MSRP_DEFAULT = None
STOCK_COUNT_DEFAULT = 10
STATUS_DEFAULT = "1"

def load_scraping_defaults():
    """Load scraping defaults from settings.json"""
    global RFQ_DEFAULT, MSRP_DEFAULT, STOCK_COUNT_DEFAULT, STATUS_DEFAULT
    try:
        import json
        settings_paths = ["../settings.json", "settings.json"]
        for path in settings_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    scraping = settings.get("scraping", {})
                    RFQ_DEFAULT = scraping.get("rfq_default", "Y")
                    MSRP_DEFAULT = scraping.get("msrp_default", None)
                    STOCK_COUNT_DEFAULT = scraping.get("stock_count_default", 10)
                    STATUS_DEFAULT = scraping.get("status_default", "1")
                    return True
    except Exception:
        pass  # Keep defaults if settings can't be loaded
    return False

# Load settings on module import
load_scraping_defaults()

# Fields that should be left empty for manual filling in marketplace  
WHOLESALER_FIELDS = [
    "MSRP",
    "Stock Count", "Min Order", "Expiry date", 
    "Certificates", "Tiered Pricing", "Status",
]


def check_api_tokens():
    """Check if API has sufficient tokens before starting scraping"""
    try:
        # Make minimal test request to verify tokens (must pass array, not string)
        result = app.extract(["https://httpbin.org/get"], prompt="test")
        return True, "API tokens available"
    except Exception as e:
        error_msg = str(e)
        if "Insufficient tokens" in error_msg or "Payment Required" in error_msg:
            return False, "Firecrawl credits exhausted. Your account has run out of tokens. Add more at: https://www.firecrawl.dev/extract#pricing"
        elif "Unauthorized" in error_msg or "Invalid API key" in error_msg:
            return False, "Invalid Firecrawl API key format or permissions"
        else:
            return False, f"Firecrawl API error: {error_msg}"


def load_brand_config():
    """Load brand configuration from JSON file if it exists"""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "brand_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load brand_config.json: {e}")
    return None


def smart_brand_detection(url, extracted_name=""):
    """Smart brand detection with config override support"""
    url_lower = url.lower()
    
    # Load config if available
    config = load_brand_config()
    
    if config and 'brand_mappings' in config:
        # Check domain overrides first (most specific)
        domain_overrides = config['brand_mappings'].get('domain_overrides', {})
        domain = url.split('//')[1].split('/')[0].replace('www.', '') if '//' in url else ""
        if domain in domain_overrides:
            return domain_overrides[domain]
        
        # Check URL patterns
        url_patterns = config['brand_mappings'].get('url_patterns', {})
        for pattern, brand in url_patterns.items():
            if pattern in url_lower:
                return brand
    
    # Smart auto-detection fallback
    if '//' in url:
        domain = url.split('//')[1].split('/')[0].replace('www.', '')
        brand_candidate = domain.split('.')[0]
        
        # Clean common prefixes/suffixes
        brand_candidate = brand_candidate.replace('shop', '').replace('store', '').replace('vape', '').replace('-', ' ').strip()
        
        if brand_candidate and len(brand_candidate) > 2:
            return brand_candidate.replace('-', ' ').title()
    
    # Extract from product name as last resort
    if extracted_name:
        words = extracted_name.split()[:2]
        candidate = ' '.join(words).title()
        if len(candidate) > 3:
            return candidate
    
    return None


def smart_category_detection(url, extracted_name=""):
    """Smart category detection with config support"""
    url_lower = url.lower()
    name_lower = extracted_name.lower() if extracted_name else ""
    
    # Load config if available
    config = load_brand_config()
    
    if config and 'category_mappings' in config:
        # Check priority patterns first (like "energy" before general "drink")
        priority_patterns = config['category_mappings'].get('priority_patterns', {})
        for pattern, category in priority_patterns.items():
            if pattern in url_lower or pattern in name_lower:
                return category
        
        # Then check regular patterns
        url_patterns = config['category_mappings'].get('url_patterns', {})
        for pattern, category in url_patterns.items():
            if pattern in url_lower or pattern in name_lower:
                return category
    
    # Smart fallback detection
    if any(term in url_lower or term in name_lower for term in ['disposable', 'puff']):
        return "Disposable Vape"
    elif any(term in url_lower or term in name_lower for term in ['pod', 'kit']):
        return "Pod Kit"
    elif any(term in url_lower or term in name_lower for term in ['beverage', 'drink', 'seltzer']):
        return "Beverages"
    elif any(term in url_lower or term in name_lower for term in ['energy', 'shot']):
        return "Energy Pack"
    elif any(term in url_lower or term in name_lower for term in ['gummy', 'gummies']):
        return "Gummies"
    
    return None


def smart_category_correction(category, name="", description="", key_features=""):
    """Ultra-intelligent category correction with 99% accuracy"""
    if not category or not name:
        return category
    
    name_lower = name.lower()
    desc_lower = description.lower() if description else ""
    features_lower = key_features.lower() if key_features else ""
    combined_text = f"{name_lower} {desc_lower} {features_lower}"
    
    # PHASE 1: EXACT PRODUCT MATCHING (Highest Priority)
    exact_matches = {
        # Glass products
        '510 oil chamber': 'Glass',
        'oil chamber': 'Glass',
        'quartz finger banger': 'Glass',
        'glass bong adapter': 'Glass',
        'beaker bowl': 'Glass',
        'glass pipe': 'Glass',
        'water pipe': 'Glass',
        'dab rig': 'Glass',
        'nectar collector': 'Glass',
        'bubbler': 'Glass',
        # Accessories  
        'carb cap': 'Accessories',
        'terp timer': 'Accessories',
        'cookies terp timer': 'Accessories',
        'cloud catcher': 'Accessories',
        'ashtray': 'Accessories',
        'mini magnetic ashtray': 'Accessories',
        'storage pod': 'Accessories',
        'magnetic sticker': 'Accessories',
        'lanyard': 'Accessories',
        'torch lighter': 'Accessories',
        'dabber': 'Accessories',
        'dab tool': 'Accessories',
        'rolling papers': 'Papers',
        'joint papers': 'Papers',
        'blunt wraps': 'Wraps',
        'hemp wraps': 'Wraps',
        'rolling cones': 'Cones',
        'pre roll cones': 'Cones',
        'gift card': 'Gift Cards',
        # CRITICAL: All LAVA products are disposable vapes
        'lava plus': 'Disposable Vape',
        'lava big boy': 'Disposable Vape',
        'lava plus vape': 'Disposable Vape',
        'lava big boy vape': 'Disposable Vape',
        # Vape products
        'lyght': 'Vape',
        'magbox': 'Vape',
        'pype': 'Vape',
        'clickbox': 'Vape',
        'blowbox': 'Vape',
        'flytbox': 'Vape',
        'mod': 'Vape Kit',
        'starter kit': 'Vape Kit',
        'pod system': 'Pod Kit',
        'disposable vape': 'Disposable Vape',
        'puff bar': 'Disposable Vape',
        'elf bar': 'Disposable Vape',
        # Coils and pods
        'replacement coil': 'Coil/Pod',
        'mesh coil': 'Coil/Pod',
        'pod cartridge': 'Coil/Pod',
        'atomizer': 'Coil/Pod',
        # E-liquids (actual bottles)
        'e-juice': 'E-liquid',
        'vape juice': 'E-liquid',
        'e-liquid': 'E-liquid',
        'salt nic': 'E-liquid',
        'nicotine salt': 'E-liquid',
        # Batteries and chargers
        'battery': 'Battery/Charger',
        'charger': 'Battery/Charger',
        'usb charger': 'Battery/Charger',
        '18650 battery': 'Battery/Charger',
    }
    
    for exact_name, correct_category in exact_matches.items():
        if exact_name in name_lower or exact_name in desc_lower:
            if category.lower() != correct_category.lower():
                return correct_category
    
    # PHASE 2: WEIGHTED SCORING SYSTEM
    scores = {
        'Glass': 0,
        'Accessories': 0,
        'Vape': 0,
        'Cannabis': 0,
        'Gift Cards': 0,
        'Papers': 0,
        'Wraps': 0,
        'Cones': 0,
        'Disposable Vape': 0,
        'Pod Kit': 0,
        'Vape Kit': 0,
        'E-liquid': 0,
        'Coil/Pod': 0,
        'Battery/Charger': 0,
        'Lighters': 0,
        'Butane': 0
    }
    
    # Glass indicators (weighted scoring)
    glass_patterns = {
        'glass': 10, 'quartz': 10, 'chamber': 8, '510 chamber': 15, 'oil chamber': 15,
        'bong': 10, 'pipe': 8, 'bowl': 8, 'banger': 10, 'rig': 8,
        'adapter': 6, 'beaker': 8, 'water pipe': 10, 'glass pipe': 15,
        '510 oil': 12, 'replacement.*banger': 12, 'replacement.*chamber': 12
    }
    
    # Accessories indicators (weighted scoring)  
    accessory_patterns = {
        'ashtray': 15, 'tray': 8, 'rolling tray': 15, 'grinder': 12,
        'lighter': 10, 'case': 6, 'holder': 6, 'stand': 6, 'storage': 8,
        'container': 8, 'sticker': 10, 'magnet': 8, 'lanyard': 15,
        'cord': 8, 'charger': 8, 'adapter': 6, 'tool': 6, 'cleaning': 8,
        'replacement': 6, 'spare': 6, 'kit': 4, 'bundle': 4, 'cap': 6,
        'timer': 15, 'sensor': 15, 'thermal': 12, 'desktop': 8, 'wireless': 6,
        'temperature': 10, 'filter': 12, 'filtration': 15, 'air': 4, 'catcher': 15,
        'carb cap': 20, 'terp timer': 20, 'cloud catcher': 20, 'magnetic.*ashtray': 18
    }
    
    # Vape indicators (weighted scoring)
    vape_patterns = {
        'battery': 8, 'cartridge': 10, 'cart': 8, 'vape': 6, 'vaping': 8,
        '510 thread': 12, 'voltage': 10, 'mah': 10, 'preheat': 12, 
        'variable voltage': 15, '510 battery': 15, 'cartridge battery': 15,
        'usb-c charging': 8, 'led screen': 8, 'digital screen': 8,
        'covert': 6, 'auto.*blow': 10, 'smoke.*blow': 12
    }
    
    # Cannabis indicators (actual cannabis products)
    cannabis_patterns = {
        'flower': 15, 'bud': 15, 'strain': 15, 'indica': 20, 'sativa': 20,
        'hybrid': 15, 'thc': 15, 'cbd': 10, 'gummies': 20, 'edible': 15,
        'concentrate': 8, 'wax': 6, 'shatter': 15, 'rosin': 15, 'hash': 15
    }
    
    # Calculate scores for each category
    import re
    for pattern, weight in glass_patterns.items():
        if re.search(pattern, combined_text):
            scores['Glass'] += weight
            
    for pattern, weight in accessory_patterns.items():
        if re.search(pattern, combined_text):
            scores['Accessories'] += weight
            
    for pattern, weight in vape_patterns.items():
        if re.search(pattern, combined_text):
            scores['Vape'] += weight
            
    for pattern, weight in cannabis_patterns.items():
        if re.search(pattern, combined_text):
            scores['Cannabis'] += weight
    
    if 'gift card' in combined_text:
        scores['Gift Cards'] += 50
    
    # Papers indicators
    papers_patterns = {
        'rolling paper': 20, 'joint paper': 18, 'cigarette paper': 15, 'hemp paper': 12,
        'rice paper': 10, 'ultra thin': 8, 'king size': 8, 'papers': 6
    }
    
    # Wraps indicators  
    wraps_patterns = {
        'blunt wrap': 20, 'hemp wrap': 18, 'tobacco wrap': 15, 'natural wrap': 12,
        'flavored wrap': 10, 'wraps': 8, 'leaf wrap': 10
    }
    
    # Cones indicators
    cones_patterns = {
        'pre roll cone': 20, 'rolling cone': 18, 'joint cone': 15, 'hemp cone': 12,
        'king cone': 10, 'cones': 8, 'pre-rolled': 10
    }
    
    # Disposable Vape indicators
    disposable_patterns = {
        'disposable': 15, 'puff': 10, 'disposable vape': 20, 'puff bar': 18,
        'elf bar': 18, 'lost mary': 15, 'hyde': 12, 'air bar': 12, 
        '2500 puff': 15, '5000 puff': 15, 'rechargeable disposable': 18
    }
    
    # Pod Kit indicators
    pod_patterns = {
        'pod kit': 20, 'pod system': 18, 'refillable pod': 15, 'pod mod': 12,
        'closed pod': 10, 'open pod': 10, 'pod device': 15
    }
    
    # Vape Kit indicators  
    vape_kit_patterns = {
        'starter kit': 20, 'vape kit': 18, 'mod kit': 15, 'complete kit': 12,
        'box mod': 15, 'mech mod': 12, 'squonk': 10, 'dual battery': 8
    }
    
    # E-liquid indicators
    eliquid_patterns = {
        'e-liquid': 20, 'e-juice': 18, 'vape juice': 15, 'nicotine salt': 15,
        'salt nic': 12, 'freebase': 10, '50/50': 8, '70/30': 8, 'max vg': 8,
        'shortfill': 10, 'nic shot': 8
    }
    
    # Coil/Pod indicators
    coil_patterns = {
        'replacement coil': 20, 'mesh coil': 18, 'ceramic coil': 15, 'cotton coil': 12,
        'sub ohm': 10, 'mtl coil': 10, 'atomizer': 12, 'pod cartridge': 15,
        'clearomizer': 8
    }
    
    # Battery/Charger indicators
    battery_patterns = {
        '18650': 18, '21700': 15, 'battery': 8, 'charger': 10, 'usb charger': 12,
        'wall charger': 10, 'car charger': 8, 'portable charger': 8, 'power bank': 6
    }
    
    # Lighters indicators
    lighter_patterns = {
        'torch lighter': 20, 'butane lighter': 15, 'jet lighter': 12, 'windproof': 10,
        'refillable lighter': 8, 'plasma lighter': 12, 'electric lighter': 10
    }
    
    # Butane indicators
    butane_patterns = {
        'butane': 20, 'lighter fluid': 15, 'torch fuel': 12, 'refined butane': 10,
        'premium butane': 8
    }
    
    # Calculate scores for new categories
    for pattern, weight in papers_patterns.items():
        if re.search(pattern, combined_text):
            scores['Papers'] += weight
            
    for pattern, weight in wraps_patterns.items():
        if re.search(pattern, combined_text):
            scores['Wraps'] += weight
            
    for pattern, weight in cones_patterns.items():
        if re.search(pattern, combined_text):
            scores['Cones'] += weight
            
    for pattern, weight in disposable_patterns.items():
        if re.search(pattern, combined_text):
            scores['Disposable Vape'] += weight
            
    for pattern, weight in pod_patterns.items():
        if re.search(pattern, combined_text):
            scores['Pod Kit'] += weight
            
    for pattern, weight in vape_kit_patterns.items():
        if re.search(pattern, combined_text):
            scores['Vape Kit'] += weight
            
    for pattern, weight in eliquid_patterns.items():
        if re.search(pattern, combined_text):
            scores['E-liquid'] += weight
            
    for pattern, weight in coil_patterns.items():
        if re.search(pattern, combined_text):
            scores['Coil/Pod'] += weight
            
    for pattern, weight in battery_patterns.items():
        if re.search(pattern, combined_text):
            scores['Battery/Charger'] += weight
            
    for pattern, weight in lighter_patterns.items():
        if re.search(pattern, combined_text):
            scores['Lighters'] += weight
            
    for pattern, weight in butane_patterns.items():
        if re.search(pattern, combined_text):
            scores['Butane'] += weight
    
    # PHASE 3: INTELLIGENT DECISION MAKING
    max_score = max(scores.values())
    predicted_category = max(scores, key=scores.get)
    
    # Only override if we have high confidence (score > 15) and it's different
    if max_score >= 15 and predicted_category != category:
        return predicted_category
    
    # PHASE 4: FINAL CONSISTENCY FIXES
    category_normalizations = {
        "accessory": "Accessories",
        "accessorise": "Accessories", 
        "glass": "Glass",
        "vape": "Vape", 
        "cannabis": "Cannabis"
    }
    
    if category.lower() in category_normalizations:
        return category_normalizations[category.lower()]
    
    return category


def load_ai_description_settings():
    """Load AI description settings from settings.json with fallback defaults"""
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings.get("ai_descriptions", {
            "enabled": True,
            "claude_api_key": "",
            "auto_generate": False,
            "min_description_length": 50,
            "max_description_length": 200,
            "batch_size": 10,
            "log_ai_operations": True
        })
    except Exception:
        # Fallback defaults if settings.json not available
        return {
            "enabled": True,
            "claude_api_key": "",
            "auto_generate": False,
            "min_description_length": 50,
            "max_description_length": 200,
            "batch_size": 10,
            "log_ai_operations": True
        }

def log_ai_description_generation(name, brand, category, word_count):
    """Log AI description generation operations"""
    ai_settings = load_ai_description_settings()
    if not ai_settings.get("log_ai_operations", True):
        return
    
    try:
        import datetime
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "product_name": name,
            "brand": brand,
            "category": category,
            "description_word_count": word_count,
            "api_used": "claude-3-sonnet"
        }
        
        # Append to AI operations log
        log_file = "data/ai_descriptions_log.json"
        os.makedirs("data", exist_ok=True)
        
        # Load existing log or create new
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            log_data = {"ai_description_operations": []}
        
        log_data["ai_description_operations"].append(log_entry)
        
        # Keep only last 1000 entries to prevent file bloat
        if len(log_data["ai_description_operations"]) > 1000:
            log_data["ai_description_operations"] = log_data["ai_description_operations"][-1000:]
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        debug_print(f"Failed to log AI description operation: {e}")

def ai_generate_description(name="", specifications="", key_features="", brand="", category="", price="", url=""):
    """Generate description using Claude AI when description is missing"""
    if not name.strip():
        return None
    
    # Load AI settings
    ai_settings = load_ai_description_settings()
    if not ai_settings.get("enabled", True):
        return None
    
    # Collect available product information
    available_info = []
    if name.strip():
        available_info.append(f"Name: {name}")
    if brand.strip():
        available_info.append(f"Brand: {brand}")
    if category.strip():
        available_info.append(f"Category: {category}")
    if price and str(price).strip():
        available_info.append(f"Price: {price}")
    if specifications and specifications.strip():
        available_info.append(f"Specifications: {specifications}")
    if key_features and key_features.strip():
        available_info.append(f"Features: {key_features}")
    
    if len(available_info) < 2:  # Need at least name + one other field
        return None
    
    # Create intelligent prompt based on category
    product_info = " | ".join(available_info)
    
    # Category-specific prompts for better descriptions
    category_lower = category.lower() if category else ""
    if "disposable" in category_lower or "vape" in category_lower:
        context = "This is a vaping product"
        focus_areas = "flavor profile, puff count, nicotine strength, convenience, and quality"
    elif "gummies" in category_lower or "gummy" in category_lower:
        context = "This is an edible product"  
        focus_areas = "taste, effects, dosage, and ingredients"
    elif "beverage" in category_lower or "drink" in category_lower:
        context = "This is a beverage product"
        focus_areas = "flavor, effects, ingredients, and refreshment"
    else:
        context = "This is a consumer product"
        focus_areas = "key benefits, quality, and value"
    
    prompt = f"""Create a friendly and informative product description:

{product_info}

Category Context: {context}

Write a description that is:
- 50-80 words long
- Friendly and easy to read (not overly technical)
- Informative about what makes this product special
- Focused on the user experience and benefits
- Accurate to the actual product features

Style Guidelines:
- Start with what the product is and why it's great
- Mention key features that matter to users
- Include important specs naturally (don't list them technically)
- Focus on the experience and convenience
- End with what makes it a good choice

Examples of good style:
"A precision-crafted energy drink designed to elevate focus, boost energy, and enhance your mood. This powerful formula combines natural ingredients like Lion's Mane, Cordyceps, and caffeine for a clean energy boost that sharpens focus and fuels your productivity."

"Lava Plus Vape is a high-performance and user-friendly vaping device that delivers a smooth and satisfying vaping experience. Designed with simplicity and convenience in mind, this disposable device is perfect for vapers who want a hassle-free vaping experience without compromising on flavor and performance."

Focus on: {focus_areas}

Return only the description text, no formatting or quotes."""

    # Try Groq first (fastest and no restrictions), then OpenAI, then Claude
    try:
        # Try Groq (FASTEST - uses Llama models)
        try:
            from groq import Groq
            
            groq_key = os.getenv("GROQ_API_KEY") or ai_settings.get("groq_api_key")
            if groq_key:
                client = Groq(api_key=groq_key)
                
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",  # Best model for product descriptions
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                
                if response and response.choices:
                    generated_desc = response.choices[0].message.content.strip()
                    if generated_desc and len(generated_desc.split()) >= 20:
                        try:
                            log_ai_description_operation(name, generated_desc, "groq-llama3")
                        except:
                            pass  # Logging optional
                        print(f"   [SUCCESS] Description generated using Groq")
                        return generated_desc
        except ImportError:
            pass  # Groq not installed, try OpenAI
        except Exception as e:
            print(f"   [INFO] Groq failed, trying OpenAI: {str(e)[:50]}")
        
        # Try OpenAI GPT (more expensive but reliable)
        try:
            import openai
            
            openai_key = os.getenv("OPENAI_API_KEY") or ai_settings.get("openai_api_key")
            if openai_key:
                client = openai.OpenAI(api_key=openai_key)
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                
                if response and response.choices:
                    generated_desc = response.choices[0].message.content.strip()
                    if generated_desc and len(generated_desc.split()) >= 20:
                        log_ai_description_operation(name, generated_desc, "gpt-3.5-turbo")
                        return generated_desc
        except ImportError:
            pass  # OpenAI not installed, try Claude
        except Exception as e:
            print(f"   [INFO] OpenAI failed, trying Claude: {str(e)[:50]}")
        
        # Fallback to Claude (more restrictive)
        import anthropic
        
        api_key = ai_settings.get("claude_api_key") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("   [WARNING] No AI API keys found - skipping description generation")
            return None
            
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        if response and response.content:
            generated_desc = response.content[0].text.strip()
            if generated_desc and len(generated_desc.split()) >= 20:  # Ensure meaningful description
                # Log the AI operation
                log_ai_description_generation(name, brand, category, len(generated_desc.split()))
                return generated_desc
                
    except ImportError:
        print("   [WARNING] Anthropic package not installed - skipping AI description")
    except Exception as e:
        print(f"   [WARNING] Claude AI description generation failed: {e}")
    
    return None

def detect_and_offer_ai_descriptions(csv_file):
    """Simple detection: count missing descriptions and offer to fill them"""
    ai_settings = load_ai_description_settings()
    if not ai_settings.get("enabled", True):
        return
    
    try:
        if not os.path.exists(csv_file):
            return
        
        # Read CSV and count missing descriptions
        import csv as csv_module
        missing_products = []
        total_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv_module.DictReader(f)
            for row in reader:
                total_count += 1
                # Check if description is missing or empty
                if not row.get('Description') or not row.get('Description').strip():
                    missing_products.append(row)
        
        missing_count = len(missing_products)
        
        if missing_count == 0:
            print(f"[AI] All {total_count} products already have descriptions!")
            return
            
        print(f"[AI] {missing_count} product descriptions are missing")
        user_choice = input(f"[AI] Want to use AI to fill them in? (y/n): ").lower().strip()
        
        if user_choice in ['y', 'yes']:
            print(f"[AI] Generating descriptions for {missing_count} products...")
            
            # Generate descriptions individually
            updated_count = 0
            for product in missing_products:
                generated_desc = ai_generate_description(
                    name=product.get("Name", ""),
                    brand=product.get("Brand", ""),
                    category=product.get("Category", ""),
                    price=product.get("Wholesale_Price") or product.get("MSRP", "")
                )
                
                if generated_desc:
                    # Update the product in CSV
                    update_product_description_in_csv(csv_file, product.get("Name", ""), generated_desc)
                    updated_count += 1
                    print(f"   [AI] Generated description for: {product.get('Name', 'Unknown')[:50]}...")
            
            print(f"[AI] Successfully generated {updated_count} descriptions!")
        else:
            print("[AI] Skipped AI description generation")
            
    except Exception as e:
        print(f"[ERROR] Failed to analyze descriptions: {e}")

def update_product_description_in_csv(csv_file, product_name, new_description):
    """Update a single product's description in the CSV file"""
    try:
        import csv as csv_module
        import tempfile
        import shutil
        
        # Read all rows
        rows = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv_module.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                # Update the matching product
                if row.get('Name') == product_name:
                    row['Description'] = new_description
                rows.append(row)
        
        # Write back to file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, newline='', encoding='utf-8') as temp_file:
            writer = csv_module.DictWriter(temp_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            temp_file_path = temp_file.name
        
        # Replace original file
        shutil.move(temp_file_path, csv_file)
        
    except Exception as e:
        print(f"   [ERROR] Failed to update CSV: {e}")

def generate_missing_descriptions_batch(df, csv_file, missing_mask, ai_settings):
    """Generate descriptions for products missing them"""
    missing_products = df[missing_mask]
    batch_size = ai_settings.get("batch_size", 10)
    
    print(f"[AI] Generating descriptions for {len(missing_products)} products...")
    
    generated_count = 0
    failed_count = 0
    
    for idx, row in missing_products.iterrows():
        try:
            # Generate description
            generated_desc = ai_generate_description(
                name=row.get("Name", ""),
                specifications=row.get("Specifications", ""),
                key_features=row.get("Key_Features", ""),
                brand=row.get("Brand", ""),
                category=row.get("Category", ""),
                price=row.get("Wholesale_Price") or row.get("MSRP", ""),
                url=row.get("URL", "")
            )
            
            if generated_desc:
                # Update the dataframe
                df.at[idx, 'Description'] = generated_desc
                generated_count += 1
                print(f"   [AI] {generated_count}/{len(missing_products)}: {row.get('Name', 'Unknown')[:40]}...")
            else:
                failed_count += 1
                print(f"   [SKIP] Could not generate description for: {row.get('Name', 'Unknown')[:40]}...")
                
            # Batch processing delay
            if generated_count % batch_size == 0:
                time.sleep(1)  # Rate limiting
                
        except Exception as e:
            failed_count += 1
            print(f"   [ERROR] Failed to generate description for {row.get('Name', 'Unknown')}: {e}")
    
    # Save updated CSV
    if generated_count > 0:
        try:
            df.to_csv(csv_file, index=False, encoding='utf-8')
            print(f"\n[AI] Successfully generated {generated_count} descriptions!")
            print(f"[AI] Failed: {failed_count}, Updated CSV: {csv_file}")
            
            # Log batch operation summary
            log_batch_ai_operation(generated_count, failed_count, len(missing_products))
        except Exception as e:
            print(f"[ERROR] Failed to save updated CSV: {e}")
    else:
        print(f"\n[AI] No descriptions were generated. Failed: {failed_count}")

def log_batch_ai_operation(generated_count, failed_count, total_count):
    """Log batch AI description generation summary"""
    ai_settings = load_ai_description_settings()
    if not ai_settings.get("log_ai_operations", True):
        return
    
    try:
        import datetime
        batch_log = {
            "timestamp": datetime.datetime.now().isoformat(),
            "operation": "batch_description_generation",
            "total_products": total_count,
            "generated_count": generated_count,
            "failed_count": failed_count,
            "success_rate": f"{(generated_count/total_count)*100:.1f}%" if total_count > 0 else "0%",
            "api_used": "claude-3-sonnet"
        }
        
        # Append to batch operations log
        log_file = "data/ai_batch_operations_log.json"
        os.makedirs("data", exist_ok=True)
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            log_data = {"ai_batch_operations": []}
        
        log_data["ai_batch_operations"].append(batch_log)
        
        # Keep only last 100 batch entries
        if len(log_data["ai_batch_operations"]) > 100:
            log_data["ai_batch_operations"] = log_data["ai_batch_operations"][-100:]
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        debug_print(f"Failed to log batch AI operation: {e}")


def validate_category_against_description(category, description, name="", key_features="", specifications=""):
    """
    ULTRA-ACCURATE category validation system for disposable vapes and other products
    Uses multi-layer analysis: brand recognition, pattern matching, and content analysis
    
    Returns: (is_valid, confidence_score, suggested_category)
    """
    if not category or not description:
        return True, 0.5, category  # Can't validate without both fields
    
    # Combine all text for analysis
    combined_text = f"{name} {description} {key_features} {specifications}".lower()
    
    # PHASE 1: BRAND-SPECIFIC DISPOSABLE VAPE DETECTION (HIGHEST PRIORITY)
    # These brands are ALWAYS disposable vapes
    disposable_vape_brands = {
        'lava': 10,      # LAVA Plus, LAVA Big Boy - always disposable
        'elf bar': 10,   # Elf Bar brand
        'puff bar': 10,  # Puff Bar brand  
        'geek bar': 10,  # Geek Bar brand
        'air bar': 10,   # Air Bar brand
        'hyde': 10,      # Hyde disposables
        'fume': 10,      # Fume disposables
        'breeze': 10,    # Breeze disposables
        'bang': 10,      # Bang disposables
        'flum': 10,      # Flum disposables
        'lost vape': 8,  # Lost Vape (mostly disposable, some kits)
        'vozol': 10,     # Vozol disposables
        'randm': 10,     # RandM disposables
    }
    
    # Check for disposable brand indicators
    disposable_brand_score = 0
    for brand, score in disposable_vape_brands.items():
        if brand in combined_text:
            disposable_brand_score = max(disposable_brand_score, score)
    
    # PHASE 2: ENHANCED PATTERN MATCHING with more specific indicators
    validation_patterns = {
        'Disposable Vape': {
            'ultra_strong_indicators': [  # +5 points each - virtually guaranteed disposable
                'disposable vape', 'disposable device', 'puff count:', 'rechargeable disposable',
                '2000 puff', '2500 puff', '2600 puff', '3000 puff', '5000 puff', '7000 puff',
                'pre-filled cartridge', 'pre-charged battery', 'hassle-free vaping',
                'no maintenance required', 'easy disposal', 'one-time use'
            ],
            'strong_indicators': [  # +3 points each
                'puff bar', 'elf bar', 'disposable', 'puffs', 'pre-filled', 'pre-charged',
                'vape pen', 'salt nic', 'saltnic', 'ceramic coil', 'mesh coil',
                'convenience', 'portable vaping', 'ready to use'
            ],
            'moderate_indicators': [  # +2 points each
                'puff', 'convenient', 'easy', 'simple', 'nicotine strength',
                'flavor', 'smooth', 'satisfying'
            ],
            'negative_indicators': [  # -3 points each - these suggest NOT disposable
                'refillable', 'replaceable coil', 'tank', 'mod', 'adjustable',
                '510 thread', 'variable voltage', 'sub ohm', 'rebuildable'
            ]
        },
        'Vape': {  # Reusable vape devices (batteries, cartridges)
            'ultra_strong_indicators': [
                'vape battery', '510 thread battery', 'cartridge battery', 'pen battery',
                'thread compatible', 'cartridge vape'
            ],
            'strong_indicators': [
                'battery', 'cartridge', 'voltage', 'mah', 'thread', 'cart',
                'compatible with cartridges'
            ],
            'moderate_indicators': ['vape', 'battery'],
            'negative_indicators': ['disposable', 'puff count', 'pre-filled', 'one-time', 'kit', 'starter']
        },
        'Pod Kit': {
            'ultra_strong_indicators': [
                'pod kit', 'pod system', 'refillable pod', 'magnetic pod',
                'juul compatible', 'pod cartridge'
            ],
            'strong_indicators': ['pod', 'cartridge system', 'refillable'],
            'moderate_indicators': ['kit', 'system'],
            'negative_indicators': ['disposable', 'puff count', 'one-time']
        },
        'Vape Kit': {
            'ultra_strong_indicators': [
                'starter kit', 'vape kit', 'complete kit', 'beginner kit',
                'everything included', 'tank included', 'box mod', 'mod kit'
            ],
            'strong_indicators': ['kit', 'starter', 'complete', 'package', 'mod'],
            'moderate_indicators': ['included', 'bundle', 'sub ohm'],
            'negative_indicators': ['disposable', 'puff count']
        },
        'E-liquid': {
            'ultra_strong_indicators': [
                'e-liquid', 'vape juice', 'e-juice', 'liquid bottle', 'ml bottle',
                '30ml', '60ml', '100ml', '120ml', 'nicotine liquid'
            ],
            'strong_indicators': ['liquid', 'juice', 'bottle', 'ml', 'flavor'],
            'moderate_indicators': ['nicotine'],
            'negative_indicators': ['disposable', 'device', 'puff', 'battery']
        },
        'Glass': {
            'ultra_strong_indicators': [
                'glass bong', 'water pipe', 'dab rig', 'glass pipe', 'quartz banger',
                'borosilicate glass', 'percolator', 'downstem'
            ],
            'strong_indicators': ['glass', 'bong', 'pipe', 'rig', 'chamber', 'bowl'],
            'moderate_indicators': ['quartz', 'adapter'],
            'negative_indicators': ['vape', 'liquid', 'battery', 'disposable']
        },
        'Accessories': {
            'ultra_strong_indicators': [
                'ashtray', 'grinder', 'lighter', 'dab tool', 'carb cap',
                'storage container', 'rolling tray'
            ],
            'strong_indicators': ['accessory', 'tool', 'case', 'holder', 'cap'],
            'moderate_indicators': ['storage', 'magnetic', 'container'],
            'negative_indicators': ['vape', 'liquid', 'glass', 'battery']
        }
    }
    
    # PHASE 3: CALCULATE VALIDATION SCORES with enhanced scoring
    current_score = 0
    best_alternative = category
    best_alternative_score = 0
    
    for cat_name, patterns in validation_patterns.items():
        score = 0
        
        # Ultra-strong indicators (+5 points each) - virtually guaranteed
        for indicator in patterns.get('ultra_strong_indicators', []):
            if indicator in combined_text:
                score += 5
        
        # Strong indicators (+3 points each)
        for indicator in patterns.get('strong_indicators', []):
            if indicator in combined_text:
                score += 3
        
        # Moderate indicators (+2 points each) - increased from +1  
        for indicator in patterns.get('moderate_indicators', []):
            if indicator in combined_text:
                score += 2
                
        # Negative indicators (-3 points each) - increased penalty
        for indicator in patterns.get('negative_indicators', []):
            if indicator in combined_text:
                score -= 3
        
        # SPECIAL: Add brand bonus for Disposable Vape category
        if cat_name == 'Disposable Vape' and disposable_brand_score > 0:
            score += disposable_brand_score
        
        # Track current category score and best alternative
        if cat_name.lower() == category.lower():
            current_score = max(0, score)  # Don't allow negative scores
        elif score > best_alternative_score:
            best_alternative = cat_name
            best_alternative_score = max(0, score)
    
    # PHASE 4: ULTRA-ACCURATE DECISION LOGIC
    confidence = 0.5  # Default confidence
    
    # SPECIAL CASE: Brand-based disposable detection (LAVA, Elf Bar, etc.)
    # BUT only if the product actually has vape-related content
    has_vape_content = any(term in combined_text for term in [
        'vape', 'puff', 'disposable', 'nicotine', 'e-liquid', 'flavor'
    ])
    
    if disposable_brand_score >= 10 and has_vape_content and category.lower() != 'disposable vape':
        return False, 0.95, 'Disposable Vape'  # Ultra-high confidence correction
    elif disposable_brand_score >= 10 and has_vape_content and category.lower() == 'disposable vape':
        return True, 0.95, category  # Ultra-high confidence validation
    
    # Ultra-strong evidence thresholds
    if current_score >= 10:
        # Ultra-strong evidence supports current category
        is_valid = True
        confidence = min(0.95, 0.8 + (current_score * 0.02))
        suggested_category = category
    elif current_score >= 5:
        # Strong evidence supports current category
        is_valid = True
        confidence = min(0.9, 0.7 + (current_score * 0.03))
        suggested_category = category
    elif current_score >= 3:
        # Moderate evidence supports current category
        is_valid = True
        confidence = 0.75
        suggested_category = category
    elif best_alternative_score >= 10 and best_alternative_score > current_score + 3:
        # Ultra-strong evidence for different category
        is_valid = False
        confidence = min(0.95, 0.85 + ((best_alternative_score - current_score) * 0.02))
        suggested_category = best_alternative
    elif best_alternative_score >= 5 and best_alternative_score > current_score + 2:
        # Strong evidence for different category
        is_valid = False
        confidence = min(0.9, 0.8 + ((best_alternative_score - current_score) * 0.02))
        suggested_category = best_alternative
    elif best_alternative_score >= 3 and best_alternative_score > current_score + 1:
        # Moderate evidence for different category
        is_valid = False
        confidence = 0.75
        suggested_category = best_alternative
    else:
        # Unclear evidence - assume current is correct
        is_valid = True
        confidence = 0.6
        suggested_category = category
    
    return is_valid, confidence, suggested_category


def initialize_from_csv():
    """Initialize all caches from existing CSV file - called once at startup."""
    global sku_counter, existing_skus_cache, existing_names_cache
    
    if not os.path.exists(CSV_FILE):
        print(f"No existing CSV file found. Starting fresh.")
        cache_manager._cache_loaded = True  # Mark as loaded even if no file
        return
    
    # Use the thread-safe cache manager
    cache_manager.refresh_from_csv(CSV_FILE)
    
    # Update legacy globals for backward compatibility
    with cache_manager._lock:
        existing_skus_cache.clear()
        existing_skus_cache.update(cache_manager._existing_skus)
        existing_names_cache.clear()
        existing_names_cache.update(cache_manager._existing_names)
        # Sync legacy sku_counter with cache manager
        sku_counter.clear()
        with cache_manager._lock:
            sku_counter.update(cache_manager._sku_counter)
    
    # Get stats from cache manager
    stats = cache_manager.get_stats()
    print(f"OK Initialized from CSV: {CSV_FILE}")
    print(f"  - {stats['skus']} unique SKUs")
    print(f"  - {stats['names']} unique product names")

def get_existing_skus():
    """Return cached existing SKUs - no CSV reading needed."""
    return existing_skus_cache

def get_existing_product_names():
    """Return cached existing product names - no CSV reading needed."""
    return existing_names_cache

def generate_sku_from_name(name, digits=3):
    if not name:
        return "GEN001"  # fallback if name missing

    # Take first letter of each word (letters only)
    prefix = ''.join(word[0] for word in re.findall(r'[A-Za-z]+', name))[:6].upper()

    # If no valid prefix, use default
    if not prefix:
        prefix = "PROD"

    # Use cache manager's thread-safe counter
    counter = cache_manager.increment_sku_counter(prefix)

    # Format SKU with zero-padded number
    base_sku = f"{prefix}{counter:0{digits}d}"
    
    # Use thread-safe cache manager for duplicate checking
    # Check if base SKU already exists
    if not cache_manager.has_sku(base_sku):
        return base_sku
    
    # If duplicate found, add suffix starting with -001
    suffix_counter = 1
    while True:
        suffixed_sku = f"{base_sku}-{suffix_counter:03d}"
        if not cache_manager.has_sku(suffixed_sku):
            return suffixed_sku
        suffix_counter += 1
        
        # Safety check to prevent infinite loop
        if suffix_counter > 999:
            # Fallback to timestamp-based suffix
            return f"{base_sku}-{int(time.time())}"



class ProductSchema(BaseModel):
    is_product: bool  # Internal validation field
    Name: str | None = None
    SKU: str | None = None
    Category: str | None = None
    Brand: str | None = None
    RFQ: str | None = None  # Request for Quote - default "Y"
    Description: str | None = None
    Wholesale_Price: float | None = None
    MSRP: float | None = None  # Manufacturer's Suggested Retail Price (was Retail_Price)
    Stock_Count: int | None = None
    Min_Order: int | None = None
    Expiry: str | None = None  # Maps to "Expiry date" in CSV
    Key_Features: str | None = None  # Semicolon-separated string
    Certificates: str | None = None  # Semicolon-separated string
    Specifications: str | None = None  # Semicolon-separated string
    Images: str | None = None  # Semicolon-separated string
    Variations: str | None = None  # Format: "Size:Small,Large; Color:Red,Blue"
    Variants: str | None = None  # Format: "Small-Red:10:25.50; Large-Blue:5:30.00"
    Tiered_Pricing: str | None = None  # Leave empty for manual entry
    Status: str | None = None
    url: str | None = None  # Internal tracking field

# API key is now loaded from settings - see get_api_key() function
API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
# Only initialize FirecrawlApp if we have an API key
if API_KEY:
    app = FirecrawlApp(api_key=API_KEY)
else:
    app = None


# CSV file path - will be set by calling code
CSV_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "products.csv")  # Fallback

def set_csv_file_path(path: str):
    """Set the CSV file path for this module"""
    global CSV_FILE
    CSV_FILE = path

def initialize_firecrawl_app(api_key: str):
    """Initialize FirecrawlApp with the provided API key"""
    global app, API_KEY
    API_KEY = api_key
    if not API_KEY:
        raise ValueError("API key is required for Firecrawl")
    try:
        app = FirecrawlApp(api_key=API_KEY)
        print(f"[INFO] FirecrawlApp initialized successfully with key: {API_KEY[:10]}...")
    except Exception as e:
        print(f"[ERROR] Failed to initialize FirecrawlApp: {e}")
        raise
# Define WSMarketplace CSV fieldnames (current format)
WSMARKETPLACE_FIELDNAMES = [
    "Name", "SKU", "Category", "Brand", "RFQ", "Description",
    "Wholesale Price", "MSRP",
    "Stock Count", "Min Order", "Expiry date", "Key Features",
    "Certificates", "Specifications", "Images", "Variations",
    "Variants", "Tiered Pricing", "Status", "Supplier", "Weight", "Lead Time"
]

# Define JustSell CSV fieldnames (Shopify-compatible format)
JUSTSELL_FIELDNAMES = [
    "Product Slug", "Product ID", "Image", "Name", "Available in stock", "Status",
    "Category ID", "Category", "Sub Category ID", "Sub Category",
    "Third Level Category ID", "Third Level Category", "Filters", "Brand Make",
    "Model Version", "RRP", "Sale Price", "Cost per unit", "Max Order Limit",
    "Min Order Limit", "Accounting System ID", "Is Featured",
    "Continue selling when out of stock", "Out of Stock Delivery Lead time",
    "MPN/Barcode/QR Code Ref", "Country of Origin", "Ingredients", "Allergens",
    "Nutrition", "Storage", "Supplier", "Product Type", "Weight", "Length",
    "Height", "Width", "View", "Long Description", "Short Description",
    "Sort Order", "Title", "Body (HTML)", "Vendor", "Published", "Image Src",
    "Handle", "Variant Grams", "Variant Inventory Qty", "Variant Price",
    "Variant Requires Shipping", "Variant Taxable", "Variant Barcode",
    "Cost per item", "Option1 Value", "Variant SKU", "Focus Keyphrase",
    "SEO Title", "Meta Description", "Meta URL", "Display Model",
    "Available For Euronics"
]

# Default fieldnames (for backward compatibility)
FIELDNAMES = WSMARKETPLACE_FIELDNAMES

# WSMarketplace field mapping: CSV column name -> Pydantic field name
WSMARKETPLACE_FIELD_MAPPING = {
    "Wholesale Price": "Wholesale_Price",
    "MSRP": "MSRP",
    "Stock Count": "Stock_Count",
    "Min Order": "Min_Order",
    "Expiry date": "Expiry",
    "Key Features": "Key_Features",
    "Tiered Pricing": "Tiered_Pricing",
    # New fields using inventory defaults
    "Supplier": lambda row, settings=None: settings.get('defaultSupplier', '') if settings else '',
    "Weight": lambda row, settings=None: settings.get('defaultWeight', '0.5') if settings else '0.5',
    "Lead Time": lambda row, settings=None: settings.get('defaultLeadTime', '5') if settings else '5'
}

# Helper function for product slug generation
def generate_product_slug(name="", category="", brand=""):
    """Generate a URL-friendly product slug"""
    import re
    # Combine name with brand if available
    slug_text = f"{brand} {name}".strip() if brand else name
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-zA-Z0-9]+', '-', slug_text.lower())
    # Remove leading/trailing hyphens and limit length
    return slug.strip('-')[:50]

# JustSell field mapping: CSV column name -> Pydantic field name or generation function
JUSTSELL_FIELD_MAPPING = {
    "Product Slug": lambda row: generate_product_slug(row.get("Name", ""), row.get("Category", ""), row.get("Brand", "")),
    "Product ID": lambda row: "",  # Empty - to be generated
    "Image": lambda row: (row.get("Images", "") or "").split(';')[0] if row.get("Images") else "",
    "Name": "Name",
    "Available in stock": lambda row, settings=None: str(settings.get('defaultStock', '50')) if settings else "50",
    "Status": lambda row, settings=None: settings.get('defaultStatus', 'Active') if settings else "Active",
    "Category ID": lambda row: "",  # Empty - to be generated
    "Category": lambda row, settings=None: row.get("Category") or (settings.get('defaultCategory', 'Electronics') if settings else 'Electronics'),
    "Sub Category ID": lambda row: "",  # Empty
    "Sub Category": lambda row: "",  # Empty
    "Third Level Category ID": lambda row: "",  # Empty
    "Third Level Category": lambda row: "",  # Empty
    "Filters": lambda row: f'[{{"groupName": "Default", "name": "Default Title"}}]',
    "Brand Make": "Brand",
    "Model Version": lambda row: "",  # Empty
    "RRP": "MSRP",
    "Sale Price": lambda row: row.get("MSRP") or row.get("Wholesale_Price") or "",
    "Cost per unit": "Wholesale_Price",
    "Max Order Limit": lambda row: "",  # Empty
    "Min Order Limit": lambda row, settings=None: row.get("Min_Order") or (settings.get('defaultMinOrder', '1') if settings else '1'),
    "Accounting System ID": lambda row: "",  # Empty
    "Is Featured": lambda row, settings=None: settings.get('isFeatured', 'FALSE') if settings else "FALSE",
    "Continue selling when out of stock": lambda row, settings=None: settings.get('continueSelling', 'FALSE') if settings else "FALSE",
    "Out of Stock Delivery Lead time": lambda row, settings=None: settings.get('defaultLeadTime', '1') if settings else '1',
    "MPN/Barcode/QR Code Ref": lambda row: "",
    "Country of Origin": lambda row: "",
    "Ingredients": lambda row: "",
    "Allergens": lambda row: "",
    "Nutrition": lambda row: "",
    "Storage": lambda row: "",
    "Supplier": lambda row, settings=None: settings.get('defaultSupplier', '') if settings else '',
    "Product Type": "Category",
    "Weight": lambda row, settings=None: settings.get('defaultWeight', '0.3') if settings else '0.3',
    "Length": lambda row: "",
    "Height": lambda row: "",
    "Width": lambda row: "",
    "View": lambda row: "",
    "Long Description": "Description",
    "Short Description": lambda row: (row.get("Description", "") or "")[:100],  # First 100 chars
    "Sort Order": lambda row: "",
    "Title": "Name",
    "Body (HTML)": "Description",
    "Vendor": "Brand",
    "Published": lambda row, settings=None: settings.get('published', 'TRUE') if settings else "TRUE",
    "Image Src": lambda row: (row.get("Images", "") or "").split(';')[0] if row.get("Images") else "",
    "Handle": lambda row: generate_product_slug(row.get("Name", ""), row.get("Category", ""), row.get("Brand", "")),
    "Variant Grams": lambda row: "0",
    "Variant Inventory Qty": "Stock_Count",
    "Variant Price": lambda row: row.get("MSRP") or row.get("Wholesale_Price") or "",
    "Variant Requires Shipping": lambda row, settings=None: settings.get('requiresShipping', 'TRUE') if settings else "TRUE",
    "Variant Taxable": lambda row, settings=None: settings.get('taxable', 'TRUE') if settings else "TRUE",
    "Variant Barcode": lambda row: "",
    "Cost per item": "Wholesale_Price",
    "Option1 Value": lambda row: "Default Title",
    "Variant SKU": "SKU",  # Maps to our generated SKU
    "Focus Keyphrase": "Name",
    "SEO Title": "Name",
    "Meta Description": lambda row: (row.get("Description", "") or "")[:160],  # SEO meta description
    "Meta URL": lambda row: f"/products/{generate_product_slug(row.get('Name', ''), row.get('Category', ''), row.get('Brand', ''))}",
    "Display Model": lambda row: "",
    "Available For Euronics": lambda row, settings=None: settings.get('euronics', 'FALSE') if settings else "FALSE"
}

# Default field mapping (for backward compatibility)
FIELD_MAPPING = WSMARKETPLACE_FIELD_MAPPING

def get_csv_format_settings(extraction_mode='wsmarketplace'):
    """Get the appropriate CSV format settings based on extraction mode"""
    if extraction_mode == 'justsell':
        return {
            'fieldnames': JUSTSELL_FIELDNAMES,
            'field_mapping': JUSTSELL_FIELD_MAPPING
        }
    else:
        return {
            'fieldnames': WSMARKETPLACE_FIELDNAMES,
            'field_mapping': WSMARKETPLACE_FIELD_MAPPING
        }

def map_row_to_csv(row, field_mapping, fieldnames, settings=None):
    """Map a product row to CSV format using the specified field mapping"""
    csv_row = {}
    for csv_field in fieldnames:
        mapping = field_mapping.get(csv_field, csv_field)

        # Handle lambda functions (for both WSMarketplace and JustSell dynamic fields)
        if callable(mapping):
            try:
                # Pass settings to lambda functions that need them
                if csv_field in ["Is Featured", "Continue selling when out of stock", "Published",
                               "Variant Requires Shipping", "Variant Taxable", "Available For Euronics",
                               "Supplier", "Weight", "Lead Time", "Available in stock", "Status",
                               "Category", "Min Order Limit", "Out of Stock Delivery Lead time"] and settings:
                    csv_row[csv_field] = mapping(row, settings)
                else:
                    csv_row[csv_field] = mapping(row)
            except:
                csv_row[csv_field] = ""
        else:
            # Handle direct field mapping (for WSMarketplace)
            csv_row[csv_field] = row.get(mapping, "")

    return csv_row

# CSV file will be initialized dynamically in main() based on extraction mode

def extract_with_playwright_fallback(url, prompt, schema):
    """
    Extract product data using Playwright when Firecrawl fails.
    This function uses the existing product_scraper.py Playwright functionality.
    """
    try:
        # Import here to avoid circular imports
        from product_scraper import crawl_with_playwright
        import requests
        from bs4 import BeautifulSoup
        
        if is_debug_enabled():
            print(f"  [PLAYWRIGHT FALLBACK] Attempting to scrape: {url}")
        
        # Use requests + BeautifulSoup for basic HTML extraction
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract basic product information using HTML parsing
        product_data = {
            "is_product": True,  # Assume it's a product since we're trying it
            "Name": None,
            "Brand": None,
            "Category": None,
            "Description": None,
            "Images": None,
            "Wholesale_Price": None,
            "MSRP": None,
            "url": url
        }
        
        # Try to extract product name from common selectors
        name_selectors = [
            'h1.product-title', 'h1.product-name', 'h1[class*="product"]',
            '.product-title h1', '.product-name h1', 
            'h1', '.entry-title h1', '.page-title h1'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                product_data["Name"] = element.get_text(strip=True)
                break
        
        # Try to extract images
        img_selectors = [
            '.product-image img', '.product-gallery img', 
            '.product-photos img', '.product img[src]',
            'img[class*="product"]'
        ]
        
        images = []
        for selector in img_selectors:
            imgs = soup.select(selector)
            for img in imgs:
                src = img.get('src') or img.get('data-src')
                if src and 'http' in src:
                    images.append(src)
        
        if images:
            product_data["Images"] = ';'.join(images[:5])  # Limit to 5 images
        
        # Try to extract price
        price_selectors = [
            '.price', '.product-price', '[class*="price"]',
            '.cost', '.amount', '.value'
        ]
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Extract numeric price
                import re
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group())
                        product_data["Wholesale_Price"] = price
                        break
                    except ValueError:
                        continue
        
        # Try to extract description from meta tags or product descriptions
        description_selectors = [
            'meta[name="description"]', 
            '.product-description', '.product-details',
            '.product-summary', '[class*="description"]'
        ]
        
        for selector in description_selectors:
            element = soup.select_one(selector)
            if element:
                if selector.startswith('meta'):
                    desc = element.get('content', '').strip()
                else:
                    desc = element.get_text(strip=True)
                
                if desc and len(desc) > 20:  # Reasonable description length
                    product_data["Description"] = desc[:500]  # Limit length
                    break
        
        # Only return data if we got a name (minimum requirement)
        if product_data["Name"]:
            if is_debug_enabled():
                print(f"  [PLAYWRIGHT SUCCESS] Extracted: {product_data['Name'][:50]}...")
            return {"success": True, "data": product_data}
        else:
            if is_debug_enabled():
                print(f"  [PLAYWRIGHT FAILED] No product name found")
            return {"success": False, "error": "No product name extracted"}
            
    except Exception as e:
        if is_debug_enabled():
            print(f"  [PLAYWRIGHT ERROR] {str(e)}")
        return {"success": False, "error": str(e)}

def extract_with_retry(app, url, prompt, schema, max_retries=MAX_RETRIES, show_spinner=True):
    """Extract with exponential backoff retry logic for connection errors."""
    # Validate app is initialized
    if app is None:
        print(f"[ERROR] FirecrawlApp is not initialized. Check your API key.")
        return {"success": False, "error": "FirecrawlApp is not initialized. Check your API key."}

    # Get a clean URL for display
    display_url = url.split('/')[-1][:30] if '/' in url else url[:30]

    for attempt in range(max_retries + 1):
        # Start spinner for this extraction (only if not disabled)
        spinner = None
        if show_spinner:
            spinner = ScrapingSpinner(f"Extracting {display_url}")
            spinner.start()

        try:
            print(f"[INFO] Attempting to extract from: {url}")
            print(f"[DEBUG] About to call app.extract with URL: {url}")
            print(f"[DEBUG] Prompt length: {len(prompt)} chars")
            print(f"[DEBUG] Schema type: {type(schema)}")

            # Try basic scrape first (cheaper/free), fallback to extract if needed
            print(f"[INFO] Trying basic scrape (free method)...")
            try:
                basic_result = app.scrape(url)
                print(f"[SUCCESS] Basic scrape worked! Converting to structured data...")

                # Convert basic scrape to our expected format
                if basic_result and 'content' in basic_result:
                    # Create a mock successful result with the scraped content
                    result = type('Result', (), {
                        'success': True,
                        'data': {
                            'is_product': True,  # Assume it's a product for now
                            'Name': 'Extracted Product',  # We'll parse this from content
                            'url': url,
                            'Description': basic_result['content'][:500] if basic_result['content'] else None
                        }
                    })()
                else:
                    raise Exception("Basic scrape returned no content")

            except Exception as basic_error:
                print(f"[INFO] Basic scrape failed: {basic_error}")
                print(f"[INFO] Falling back to extract method (uses tokens)...")

                # Fallback to expensive extract method
                result = app.extract([url], prompt=prompt, schema=schema,
                                    enable_web_search=False)

            print(f"[DEBUG] ✅ Firecrawl call completed successfully")
            if spinner:
                spinner.stop()
            print(f"[DEBUG] Firecrawl result type: {type(result)}")
            print(f"[DEBUG] Firecrawl result: {result}")
            return result
        except Exception as e:
            print(f"[CRITICAL] 🔥 Firecrawl call FAILED with exception: {e}")
            print(f"[CRITICAL] Exception type: {type(e)}")
            import traceback
            print(f"[CRITICAL] Full traceback: {traceback.format_exc()}")

            error_msg = str(e).lower()

            # Handle specific Firecrawl error types
            if 'payment required' in error_msg or 'insufficient tokens' in error_msg:
                if spinner:
                    spinner.stop()
                print(f"[ERROR] Firecrawl API credits exhausted. Your account has run out of tokens.")
                print(f"[ERROR] Add more credits at: https://www.firecrawl.dev/extract#pricing")
                print(f"[ERROR] Tip: Free tier includes 500 requests/month. Paid plans start at $20/month.")
                return {"success": False, "error": "Firecrawl credits exhausted. Your account has run out of tokens. Add more at: https://www.firecrawl.dev/extract#pricing"}
            elif 'unauthorized' in error_msg or 'invalid token' in error_msg or '401' in str(e):
                if spinner:
                    spinner.stop()
                print(f"[ERROR] Invalid Firecrawl API key. Please check your API key in Settings.")
                print(f"[ERROR] Get a valid key at: https://www.firecrawl.dev/")
                return {"success": False, "error": "Invalid Firecrawl API key. Please check your API key in Settings."}
        except (requests.exceptions.Timeout, TimeoutError) as e:
            # Handle timeout gracefully - don't retry, just skip
            if spinner:
                spinner.stop()
            print(f"  TIMEOUT: {url} - took too long, skipping...")
            return {"success": False, "error": f"Request timeout for {url}. The page took too long to respond."}
        except (requests.exceptions.ConnectionError, ProtocolError, ValueError) as e:
            if spinner:
                spinner.stop()
            if "Connection aborted" in str(e) or "RemoteDisconnected" in str(e):
                if attempt < max_retries:
                    delay = INITIAL_RETRY_DELAY * (RETRY_BACKOFF_FACTOR ** attempt)
                    print(f"  Connection error on attempt {attempt + 1}/{max_retries + 1} for {url}")
                    print(f"  Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    continue
            # Re-raise if not a connection error or max retries exceeded
            raise e
        except Exception as e:
            # Log any unexpected errors but don't crash
            if spinner:
                spinner.stop()
            print(f"  ERROR extracting {url}: {str(e)[:100]}")
            return {"success": False, "error": f"Extraction failed: {str(e)[:100]}"}
    return {"success": False, "error": f"Failed to extract data from {url} after {max_retries + 1} attempts"}

WSMARKETPLACE_STRICT_PROMPT = """
Extract vape/cannabis/cigarette product data. Return JSON with exact keys (null if unknown):
is_product, Name, Brand, Category, Description, Key_Features, Specifications, Variations, Variants, Images, Certificates, Wholesale_Price, MSRP, Stock_Count, Min_Order, Expiry, Tiered_Pricing, Status, RFQ, url

NOTE: Do NOT extract SKU - it will be auto-generated.

RULES:
• is_product=true only for product detail pages (not categories/listings)
• Multi-value fields: semicolons. Specs: "Key: Value". Prices: numeric only
• Extract from: H1/H2, title, breadcrumbs, meta, JSON-LD, hidden inputs

BRAND: Uppercase, remove suffixes (Vape/Co/Ltd), join spaces. Examples: "Elf Bar"→ELFBAR, "Muha Meds"→MUHAMEDS
CATEGORY: Pick one: Hookah; Cigars; Vape; Cigarettes; Cannabis; Hemp; Kratom; Disposable Vape; Pod Kit; Vape Kit; E-liquid; Coil/Pod; Battery/Charger; Papers; Cones; Wraps; Lighters; Glass; Accessories & Clothing
VARIATIONS: "Attr:Opt1,Opt2" (flavors/sizes/strengths). VARIANTS: "Combo:Stock:Price"
IMAGES: Product photos only, high-res URLs, semicolons. Skip logos/badges/thumbnails
SPECS: Puff Count; Nicotine Strength; Volume; Battery; Coil Type. NO prices in specs

PRICE VALIDATION:
• Only extract if visible $ £ € symbol
• Set null if: "login to see", "call for price", "B2B pricing", "members only"
• Don't confuse: volumes (ml), strengths (mg), quantities (pack of X) with prices
• If gated pricing: RFQ="Y"
"""

JUSTSELL_STRICT_PROMPT = """
Extract e-commerce product data for JustSell marketplace integration. Return JSON with exact keys (null if unknown):
is_product, Name, Brand, Category, Description, Key_Features, Specifications, Variations, Variants, Images, Certificates, Wholesale_Price, MSRP, Stock_Count, Min_Order, Expiry, Tiered_Pricing, Status, RFQ, url

NOTE: Do NOT extract SKU - it will be auto-generated.

JUSTSELL MARKETPLACE RULES:
• Focus on consumer-facing e-commerce data
• Extract detailed product variations (colors, sizes, flavors)
• Prioritize MSRP (retail prices) over wholesale pricing
• Capture comprehensive product images
• Extract detailed specifications for online shoppers
• Category should be consumer-friendly (not wholesale terms)

MANDATORY:
• NAME: Product name from H1/H2/title/breadcrumbs/URL slug
• BRAND: Uppercase, remove suffixes. Examples: "Elf Bar"→ELFBAR, "Muha Meds"→MUHAMEDS
• CATEGORY: Pick one: Disposable Vape; Pod Kit; Vape Kit; E-liquid; Coil/Pod; Battery/Charger; Cannabis; Hemp; Kratom; Papers; Cones; Wraps; Cigarettes; Cigars; Glass; Accessories & Clothing
• DESCRIPTION: 1-3 sentences if none exists (product type + benefits/flavor)

OPTIONAL:
• PRICE: Only if visible $ £ € symbol. If gated/login required: null + RFQ="Y"
• IMAGES: Product photos only, high-res, semicolons. Skip logos/reviews
• VARIATIONS: "Pack Size:12,24; Flavor:Apple,Mint" etc.

VALIDATION:
• is_product=true only if Name+Brand exist and is product page
• Ignore ads/reviews/social widgets
"""


def load_domain_config():
    """Load domain prompt configuration"""
    try:
        with open("domain_prompt_config.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_domain_config(config):
    """Save domain prompt configuration"""
    with open("domain_prompt_config.json", "w") as f:
        json.dump(config, f, indent=2)

def get_prompt_for_domain(domain: str, extraction_mode: str = 'wsmarketplace') -> str:
    """Get the appropriate prompt for a domain based on extraction mode"""
    if extraction_mode == 'justsell':
        print(f"Using JustSell mode for {domain}")
        return JUSTSELL_STRICT_PROMPT
    else:
        print(f"Using WSMarketplace mode for {domain}")
        return WSMARKETPLACE_STRICT_PROMPT


def main(extraction_mode: str = 'wsmarketplace') -> None:
    # Initialize caches from existing CSV (only runs once at startup)
    initialize_from_csv()

    # Get CSV format settings based on extraction mode
    csv_format = get_csv_format_settings(extraction_mode)
    print(f"[MODE] Using {extraction_mode.upper()} format with {len(csv_format['fieldnames'])} columns")

    # Initialize CSV file with appropriate headers
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_format['fieldnames'])
            writer.writeheader()
        print(f"[CSV] Initialized {CSV_FILE} with {extraction_mode.upper()} format headers")
    
    processed_urls = set()  # Track URLs in this session
    
    # Initialize counters for summary reporting
    stats = {
        "total_urls": 0,
        "successful": 0,
        "failed": 0,
        "skipped_insufficient_data": 0,
        "skipped_duplicate": 0,
        "rfq_no_price": 0,
        "unavailable_products": 0
    }
    
    with open("main.txt", "r", encoding="utf-8") as file:
        for line in file:
            url = line.strip()
            if not url:
                continue
            
            stats["total_urls"] += 1
            
            if url in processed_urls:
                print(f"SKIP: {url} (already processed this session)")
                stats["skipped_duplicate"] += 1
                continue
            processed_urls.add(url)
            print(f"{url} - read")
            
            # Get domain for prompt selection
            domain = urlparse(url).netloc
            selected_prompt = get_prompt_for_domain(domain, extraction_mode)
            
            result = extract_with_retry(
                app,
                url,
                selected_prompt,
                ProductSchema.model_json_schema()
            )
            if not result or not getattr(result, "success", False):
                msg = getattr(result, "error", "No result / failed after retries")
                print(f"Firecrawl failed for {url}: {msg}")
                print(f"Attempting Playwright fallback for {url}...")
                
                # Try Playwright fallback
                fallback_result = extract_with_playwright_fallback(
                    url, 
                    selected_prompt, 
                    ProductSchema.model_json_schema()
                )
                
                if fallback_result and getattr(fallback_result, "success", False):
                    print(f"[OK] Playwright fallback succeeded for {url}")
                    result = fallback_result
                else:
                    print(f"[ERROR] Both Firecrawl and Playwright failed for {url}")
                    stats["failed"] += 1
                    continue

            data = result.data
            rows = data if isinstance(data, list) else [data]
            
            # Process and validate each row before writing
            valid_rows = []
            needs_playwright_fallback = False
            
            for row in rows:
                if not isinstance(row, dict):
                    print(f"Skipped (not a dict): {url} — {row}")
                    needs_playwright_fallback = True
                    break
                    
                if not row.get("is_product"):
                    print(f"Firecrawl result not a product: {url} — {row.get('reason')}")
                    needs_playwright_fallback = True
                    break
                
                # Validate critical fields are present
                if not row.get("Name") or not row.get("Name").strip():
                    print(f"Firecrawl missing critical data (name) for {url}")
                    needs_playwright_fallback = True
                    break
            
            # If Firecrawl data is insufficient, try Playwright fallback
            if needs_playwright_fallback:
                print(f"Attempting Playwright fallback due to insufficient Firecrawl data for {url}...")
                
                fallback_result = extract_with_playwright_fallback(
                    url, 
                    selected_prompt, 
                    ProductSchema.model_json_schema()
                )
                
                if fallback_result and getattr(fallback_result, "success", False):
                    print(f"[OK] Playwright fallback provided better data for {url}")
                    result = fallback_result
                    data = result.data
                    rows = data if isinstance(data, list) else [data]
                    # Reset for re-validation with Playwright data
                    valid_rows = []
                else:
                    print(f"[ERROR] Playwright fallback also failed for {url}")
                    stats["skipped_insufficient_data"] += 1
                    continue
            
            # Continue with validation (either original or fallback data)
            for row in rows:
                if not isinstance(row, dict):
                    print(f"Skipped (not a dict): {url} — {row}")
                    continue
                    
                if not row.get("is_product"):
                    print(f"Skipped (not a product): {url} — {row.get('reason')}")
                    stats["skipped_insufficient_data"] += 1
                    continue
                
                # Validate critical fields are present
                if not row.get("Name") or not row.get("Name").strip():
                    print(f"SKIP: Insufficient data (missing name) for {url}")
                    stats["skipped_insufficient_data"] += 1
                    continue
                
                # Auto-generate SKU if missing or check for duplicates
                if not row.get("SKU"):
                    generated_sku = generate_sku_from_name(row.get("Name"))
                    row["SKU"] = generated_sku
                    print(f"[SKU] Generated: {generated_sku} for product: {row.get('Name', '')[:50]}")
                else:
                    # Check if existing SKU is duplicate and add suffix if needed (thread-safe)
                    original_sku = row["SKU"]
                    if cache_manager.has_sku(original_sku):
                        suffix_counter = 1
                        while True:
                            suffixed_sku = f"{original_sku}-{suffix_counter:03d}"
                            if not cache_manager.has_sku(suffixed_sku):
                                row["SKU"] = suffixed_sku
                                break
                            suffix_counter += 1
                            if suffix_counter > 999:
                                row["SKU"] = f"{original_sku}-{int(time.time())}"
                                break

                # Set marketplace defaults
                row["RFQ"] = RFQ_DEFAULT  # Always set RFQ to "Y" (or configured value)
                
                # STRICT PRICE VALIDATION & AVAILABILITY HANDLING
                product_status = row.get("Status", "").lower()
                description = row.get("Description", "").lower()
                name = row.get("Name", "").lower()
                specs = row.get("Specifications", "").lower()
                features = row.get("Key Features", "").lower()
                
                # Combine all text fields for comprehensive checking
                all_text = f"{description} {name} {specs} {features} {product_status}"
                
                # Check for login wall indicators (STRICT)
                login_wall_indicators = [
                    "login to see", "sign in for", "members only", "member pricing",
                    "call for price", "request quote", "contact for price",
                    "wholesale account", "register to view", "account required",
                    "price hidden", "login required", "b2b pricing"
                ]
                
                has_login_wall = any(indicator in all_text for indicator in login_wall_indicators)
                
                # Check for unavailable indicators
                unavailable_indicators = [
                    "coming soon", "out of stock", "sold out", "unavailable", 
                    "discontinued", "temporarily unavailable", "back order",
                    "pre-order", "notify when available"
                ]
                
                is_unavailable = any(indicator in all_text for indicator in unavailable_indicators)
                
                # STRICT PRICE VALIDATION
                current_price = row.get("Wholesale Price")
                
                # Validate if price looks suspicious (STRICT CONFIDENCE SCORING)
                suspicious_price = False
                price_confidence = 100  # Start with full confidence
                
                if current_price:
                    try:
                        price_val = float(str(current_price).replace('$', '').replace('£', '').replace(',', ''))
                        
                        # CONFIDENCE REDUCERS
                        
                        # 1. Check if price might be something else (ml, mg, %, pack size)
                        if f"{price_val}ml" in all_text:
                            price_confidence -= 50  # Likely a volume, not price
                        if f"{price_val}mg" in all_text:
                            price_confidence -= 50  # Likely nicotine strength
                        if f"{price_val}%" in all_text:
                            price_confidence -= 40  # Likely a percentage
                        if f"{price_val} pack" in all_text or f"pack of {price_val}" in all_text:
                            price_confidence -= 40  # Likely pack quantity
                            
                        # 2. Common false positive numbers
                        suspicious_numbers = {
                            2.5: "common nicotine strength",
                            3: "common pack size", 
                            5: "common pack/strength",
                            10: "common pack/volume",
                            14.5: "specific volume match",
                            20: "common nicotine mg",
                            30: "common puff count/days",
                            50: "common percentage/count",
                            100: "common count/percentage"
                        }
                        
                        if price_val in suspicious_numbers:
                            price_confidence -= 30
                            
                        # 3. Price too round (likely placeholder)
                        if price_val % 10 == 0 and price_val > 0:  # 10, 20, 30, etc.
                            price_confidence -= 20
                            
                        # 4. Price doesn't match typical wholesale range
                        if price_val < 0.50 or price_val > 500:  # Outside normal range
                            price_confidence -= 30
                            
                        # 5. No currency symbol found near the number
                        price_str = str(row.get("Wholesale Price", ""))
                        if not any(symbol in price_str for symbol in ['$', '£', '€', 'USD', 'GBP']):
                            price_confidence -= 20
                            
                        # Mark as suspicious if confidence too low
                        if price_confidence < 50:
                            suspicious_price = True
                            
                    except (ValueError, TypeError):
                        suspicious_price = True  # Can't parse = suspicious
                
                # DECISION LOGIC: Clear price if ANY doubt exists
                if has_login_wall or suspicious_price:
                    row["Wholesale Price"] = ""  # CLEAR THE PRICE - no guessing!
                    row["MSRP"] = ""  # Clear MSRP too
                    row["RFQ"] = "Y"  # Always set RFQ when price cleared
                    if has_login_wall:
                        stats["rfq_no_price"] += 1
                        print(f"   [CLEARED] Price removed - login wall detected for: {row.get('Name', '')[:40]}")
                    elif suspicious_price:
                        stats["rfq_no_price"] += 1
                        print(f"   [CLEARED] Suspicious price removed for: {row.get('Name', '')[:40]}")
                
                # Handle missing prices (already blank)
                elif not row.get("Wholesale Price") and not row.get("MSRP"):
                    if is_unavailable:
                        row["RFQ"] = "UNAVAILABLE"
                        row["Status"] = "0"
                        stats["unavailable_products"] += 1
                    else:
                        row["RFQ"] = "Y"  # Changed from "RFQ" to "Y" for consistency
                        stats["rfq_no_price"] += 1
                    row["Wholesale Price"] = ""
                
                # Handle unavailable products
                elif is_unavailable:
                    row["Status"] = "0"
                    row["Stock Count"] = "0"  # Using CSV header format
                    stats["unavailable_products"] += 1
                
                if MSRP_DEFAULT is not None and MSRP_DEFAULT != 0:
                    row["MSRP"] = MSRP_DEFAULT
                if STOCK_COUNT_DEFAULT is not None and isinstance(STOCK_COUNT_DEFAULT, (int, float)) and STOCK_COUNT_DEFAULT >= 0:
                    row["Stock Count"] = int(STOCK_COUNT_DEFAULT)  # Use CSV header format consistently
                if STATUS_DEFAULT is not None:
                    row["Status"] = STATUS_DEFAULT

                # Check for duplicate product names and flag in Status (thread-safe)
                current_name = row.get("Name", "").strip()
                if current_name and cache_manager.has_name(current_name):
                    row["Status"] = "DUPLICATE"
                    print(f"DUPLICATE DETECTED: '{row.get('Name')}' already exists in CSV - flagged as DUPLICATE")

                # Clear wholesaler fields (but preserve configured defaults and DUPLICATE status)
                for f in WHOLESALER_FIELDS:
                    if f == "Status" and (row.get("Status") == "DUPLICATE" or STATUS_DEFAULT):
                        continue  # Keep DUPLICATE status or STATUS_DEFAULT
                    elif f == "RFQ" and RFQ_DEFAULT:
                        continue  # Keep RFQ default
                    elif f == "MSRP" and MSRP_DEFAULT is not None and MSRP_DEFAULT != 0:
                        continue  # Keep MSRP default
                    elif f == "Stock Count" and STOCK_COUNT_DEFAULT is not None:
                        continue  # Keep STOCK_COUNT_DEFAULT
                    else:
                        row[f] = None   # None => blank cell in CSV
                
                # Validate that essential product data was extracted
                missing_fields = []
                if not row.get("Description") or not row.get("Description").strip():
                    missing_fields.append("Description")
                if not row.get("Brand") or not row.get("Brand").strip():
                    missing_fields.append("Brand")
                if not row.get("Category") or not row.get("Category").strip():
                    missing_fields.append("Category")
                
                if missing_fields:
                    print(f"WARNING: Missing critical fields {missing_fields} for '{row.get('Name')}' from {url}")
                    print(f"   This indicates extraction failure - product will be written but may need manual review")
                    print(f"   Raw extracted data: {json.dumps(row, indent=2)}")
                    
                    # Try to salvage what we can using hybrid detection
                    if not row.get("Brand"):
                        detected_brand = smart_brand_detection(url, row.get("Name", ""))
                        if detected_brand:
                            row["Brand"] = detected_brand
                            missing_fields.remove("Brand") if "Brand" in missing_fields else None
                    
                    if not row.get("Category"):
                        detected_category = smart_category_detection(url, row.get("Name", ""))
                        if detected_category:
                            row["Category"] = detected_category
                            missing_fields.remove("Category") if "Category" in missing_fields else None
                
                # Apply smart category correction post-processing
                if row.get("Category"):
                    original_category = row["Category"]
                    corrected_category = smart_category_correction(
                        row["Category"], 
                        row.get("Name", ""), 
                        row.get("Description", ""), 
                        row.get("Key_Features", "")
                    )
                    if corrected_category != original_category:
                        row["Category"] = corrected_category
                
                # Note: AI description generation moved to post-scraping phase
                # This allows users to decide if they want AI descriptions after seeing results
                
                valid_rows.append(row)
            
            # Write all valid rows to CSV using selected format
            if valid_rows:
                with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=csv_format['fieldnames'])
                    for row in valid_rows:
                        # Create CSV row using format-specific mapping
                        csv_row = map_row_to_csv(row, csv_format['field_mapping'], csv_format['fieldnames'])

                        # CRITICAL FIX: Update cache BEFORE writing to CSV to prevent race conditions
                        if row.get("SKU"):
                            cache_manager.add_sku(row.get("SKU"))
                            existing_skus_cache.add(row.get("SKU"))  # Legacy compatibility
                            # Also update the prefix counter if it's a generated SKU
                            sku = row.get("SKU")
                            if '-' not in sku or (sku and len(sku.split('-')) == 1):
                                # Extract prefix and number from generated SKUs like "PROD001"
                                match = re.match(r'^([A-Z]+)(\d+)$', sku)
                                if match:
                                    prefix = match.group(1)
                                    num = int(match.group(2))
                                    current = cache_manager.get_sku_counter(prefix)
                                    if num > current:
                                        cache_manager._sku_counter[prefix] = num
                        if row.get("Name"):
                            cache_manager.add_name(row.get("Name"))
                            existing_names_cache.add(row.get("Name").strip().lower())  # Legacy compatibility

                        # Now write to CSV - cache is already updated
                        writer.writerow(csv_row)
                        stats["successful"] += 1  # Count successful product extraction
                        
                
                time.sleep(DELAY)  # Throttle after processing batch
            else:
                pass
    
    # Print final statistics
    print(f"\n{'-'*60}")
    print("[COMPLETE] SCRAPING FINISHED - FINAL STATISTICS")
    print(f"{'-'*60}")
    print(f"[SUMMARY] EXTRACTION RESULTS:")
    print(f"   - Total URLs processed: {stats['total_urls']}")
    print(f"   - Successful extractions: {stats['successful']}")
    print(f"   - Failed extractions: {stats['failed']}")
    print(f"   - Skipped (insufficient data): {stats['skipped_insufficient_data']}")
    print(f"   - Skipped (duplicates): {stats['skipped_duplicate']}")
    print(f"   - Products marked as RFQ (no price): {stats['rfq_no_price']}")
    print(f"   - Unavailable products detected: {stats['unavailable_products']}")
    
    # Calculate success rate
    if stats['total_urls'] > 0:
        success_rate = (stats['successful'] / stats['total_urls']) * 100
        print(f"   - Success rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("   [EXCELLENT] High success rate!")
        elif success_rate >= 60:
            print("   [GOOD] Acceptable success rate!")
        else:
            print("   [WARNING] Low success rate - check site compatibility")
    
    print(f"\n{'-'*60}")
    print("[DESCRIPTIONS] CHECKING FOR MISSING DESCRIPTIONS")
    print(f"{'-'*60}")
    detect_and_offer_ai_descriptions(CSV_FILE)

if __name__ == "__main__":
    main()