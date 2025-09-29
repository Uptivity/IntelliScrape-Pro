"""
Hybrid Product Page Scraper - Best of Both Worlds

INTELLIGENT HYBRID APPROACH:
1. PRIMARY: Fast pagination scraping with BeautifulSoup4 (no API cost)
2. FALLBACK: Proven Firecrawl system when pagination fails
3. SMART: Automatically chooses best method per site

STRICT REQUIREMENTS:
- Only captures INDIVIDUAL product pages (single product per page)
- Page MUST have a buy/add to cart button
- Excludes category pages, search results, and listing pages
- Excludes all media files (images, PDFs, etc.)
- Only includes pages where a user can complete a purchase
"""

import firecrawl
import re
import os
from typing import Set, List, Dict, Any, Tuple, Callable, Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlunparse, quote, unquote
import time
from tqdm import tqdm
import threading
import sys
import requests
from bs4 import BeautifulSoup
import json
import hashlib
try:
    from playwright.sync_api import sync_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("Playwright not installed. Run: pip install playwright && playwright install")

class DotSpinner:
    """Clean loading indicator with proper spacing"""
    def __init__(self, message="Loading"):
        self.message = message
        self.spinning = False
        self.spinner_thread = None
        self.frames = ['.  ', '.. ', '...', ' ..', '  .', '   ']  # Simple dots, no Unicode
        self.frame_index = 0
    
    def start(self):
        if not self.spinning:
            print(f"\n{self.message}...")  # Start on new line
            self.spinning = True
            self.spinner_thread = threading.Thread(target=self._spin)
            self.spinner_thread.daemon = True
            self.spinner_thread.start()
    
    def stop(self):
        if self.spinning:
            self.spinning = False
            if self.spinner_thread:
                self.spinner_thread.join(timeout=0.1)
            # Clear the spinner line and add space
            sys.stdout.write('\r' + ' ' * 50 + '\r')
            sys.stdout.flush()
            print()  # Add blank line after stopping
    
    def _spin(self):
        while self.spinning:
            frame = self.frames[self.frame_index]
            sys.stdout.write(f'\r{frame}')
            sys.stdout.flush()
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            time.sleep(0.5)  # Slower animation


# Import debug configuration from scraper module
try:
    from scraper import (
        is_debug_enabled, 
        enable_debug_mode as _enable_debug,
        disable_debug_mode as _disable_debug,
        load_debug_settings
    )
except ImportError:
    # Fallback if scraper not available
    _DEBUG_ENABLED = False
    def is_debug_enabled(): return _DEBUG_ENABLED
    def _enable_debug(): global _DEBUG_ENABLED; _DEBUG_ENABLED = True
    def _disable_debug(): global _DEBUG_ENABLED; _DEBUG_ENABLED = False
    def load_debug_settings(): return _DEBUG_ENABLED

# Wrapper functions to update VALIDATION_CONFIG
def enable_debug_mode():
    """Enable debug mode for detailed output during scraping"""
    _enable_debug()
    VALIDATION_CONFIG["debug_mode"] = True

def disable_debug_mode():
    """Disable debug mode for clean output"""
    _disable_debug()
    VALIDATION_CONFIG["debug_mode"] = False

# Initialize debug mode from settings
load_debug_settings()

# STRICT VALIDATION CONFIGURATION
VALIDATION_CONFIG = {
    # Debug mode - set to True to see detailed validation reasoning
    "debug_mode": is_debug_enabled(),
    
    # Minimum confidence score (0-100) required to classify as product page
    "min_confidence_score": 70,
    
    # Required elements for a valid product page
    "required_elements": {
        "buy_action": {
            "patterns": [
                r'add[\s-]?to[\s-]?cart',
                r'buy[\s-]?now', 
                r'add[\s-]?to[\s-]?bag',
                r'add[\s-]?to[\s-]?basket',
                r'purchase[\s-]?now',
                r'order[\s-]?now'
            ],
            "weight": 40  # High weight - this is critical
        }
    },
    
    # Elements that indicate a single product page
    "product_indicators": {
        "quantity_selector": {
            "patterns": [r'quantity[\s:]+', r'qty[\s:]+', r'amount[\s:]+'],
            "weight": 15
        },
        "size_selector": {
            "patterns": [r'select[\s-]?size', r'size[\s:]+', r'choose[\s-]?size'],
            "weight": 10
        },
        "color_selector": {
            "patterns": [r'select[\s-]?colou?r', r'colou?r[\s:]+', r'choose[\s-]?colou?r'],
            "weight": 10
        },
        "stock_status": {
            "patterns": [r'in[\s-]?stock', r'out[\s-]?of[\s-]?stock', r'availability[\s:]+'],
            "weight": 10
        },
        "product_id": {
            "patterns": [r'sku[\s:#]+', r'item[\s#:]+', r'product[\s#:]+', r'model[\s:#]+'],
            "weight": 15
        },
        "price_display": {
            "patterns": [r'\$[\d,]+\.?\d*', r'£[\d,]+\.?\d*', r'€[\d,]+\.?\d*', r'price[\s:]+'],
            "weight": 10
        },
        "product_details": {
            "patterns": [r'product[\s-]?details', r'description', r'specifications', r'features'],
            "weight": 5
        },
        "reviews": {
            "patterns": [r'customer[\s-]?reviews?', r'ratings?', r'testimonials?'],
            "weight": 5
        }
    },
    
    # Elements that DISQUALIFY a page from being a single product page
    "disqualifiers": {
        "pagination": {
            "patterns": [
                r'page[\s-]?\d+[\s-]?of[\s-]?\d+',
                r'showing[\s-]?\d+[\s-]?of[\s-]?\d+',
                r'results?[\s-]?\d+[\s-]?-[\s-]?\d+',
                r'next[\s-]?page',
                r'previous[\s-]?page',
                r'<[\s-]?prev',
                r'next[\s-]?>',
                r'page[\s-]?:[\s-]?\[[\s-]?\d+[\s-]?\]'
            ],
            "severity": 100  # Instant disqualification
        },
        "filtering": {
            "patterns": [
                r'filter[\s-]?by',
                r'sort[\s-]?by',
                r'refine[\s-]?results?',
                r'narrow[\s-]?by'
            ],
            "severity": 100
        },
        "multiple_products": {
            "patterns": [
                r'compare[\s-]?products?',
                r'view[\s-]?all',
                r'shop[\s-]?all',
                r'browse[\s-]?by',
                r'\d+[\s-]?items?[\s-]?found',
                r'\d+[\s-]?products?[\s-]?found',
                r'search[\s-]?results?'
            ],
            "severity": 100
        },
        "category_indicators": {
            "patterns": [
                r'browse[\s-]categories',
                r'shop[\s-]collections?',
                r'all[\s-]categories',
                r'product[\s-]categories',
                r'departments?[\s-]?listing',
                r'brands?[\s-]?listing'
            ],
            "severity": 80
        }
    }
}


def validate_product_page(content: str, url: str = "", debug: bool = None) -> Tuple[bool, int, str]:
    """
    STRICT validation to determine if a page is a SINGLE product page.
    
    Args:
        content (str): The HTML/text content of the page to analyze
        url (str): The URL of the page (optional, for additional validation)
        debug (bool): Override debug mode setting
        
    Returns:
        Tuple[bool, int, str]: (is_product_page, confidence_score, reasoning)
    """
    if debug is None:
        debug = VALIDATION_CONFIG["debug_mode"]
        
    content_lower = content.lower()
    confidence_score = 0
    reasoning = []
    
    # Step 1: Check for instant disqualifiers
    for disqualifier_name, disqualifier in VALIDATION_CONFIG["disqualifiers"].items():
        for pattern in disqualifier["patterns"]:
            if re.search(pattern, content_lower):
                reasoning.append(f"DISQUALIFIED: Found {disqualifier_name} indicator: '{pattern}'")
                if disqualifier["severity"] >= 100:
                    return False, 0, "\n".join(reasoning)
                else:
                    confidence_score -= disqualifier["severity"]
    
    # Step 2: Check for required elements (buy action)
    has_required = False
    for element_name, element in VALIDATION_CONFIG["required_elements"].items():
        for pattern in element["patterns"]:
            if re.search(pattern, content_lower):
                has_required = True
                confidence_score += element["weight"]
                reasoning.append(f"REQUIRED: Found {element_name}: '{pattern}'")
                break
    
    if not has_required:
        reasoning.append("FAILED: No buy action found (add to cart, buy now, etc.)")
        return False, confidence_score, "\n".join(reasoning)
    
    # Step 3: Check for product indicators
    found_indicators = []
    for indicator_name, indicator in VALIDATION_CONFIG["product_indicators"].items():
        for pattern in indicator["patterns"]:
            if re.search(pattern, content_lower):
                found_indicators.append(indicator_name)
                confidence_score += indicator["weight"]
                reasoning.append(f"INDICATOR: Found {indicator_name}: '{pattern}'")
                break
    
    # Step 4: Additional URL-based validation
    if url:
        if is_valid_product_url(url):
            confidence_score += 10
            reasoning.append(f"URL: Valid product URL pattern")
        else:
            confidence_score -= 20
            reasoning.append(f"URL: Does not match product URL patterns")
    
    # Step 5: Final validation
    is_valid = confidence_score >= VALIDATION_CONFIG["min_confidence_score"]
    
    reasoning.append(f"\nFINAL SCORE: {confidence_score} (minimum: {VALIDATION_CONFIG['min_confidence_score']})")
    reasoning.append(f"RESULT: {'VALID PRODUCT PAGE' if is_valid else 'NOT A PRODUCT PAGE'}")
    
    if debug:
        print(f"\n=== Validation Debug for {url or 'content'} ===")
        print("\n".join(reasoning))
        print("=" * 50)
    
    return is_valid, confidence_score, "\n".join(reasoning)


def is_product_page(content: str, url: str = "") -> bool:
    """
    Wrapper for backward compatibility. Uses strict validation.
    
    Args:
        content (str): The HTML/text content of the page to analyze
        url (str): The URL of the page (optional, for additional validation)
        
    Returns:
        bool: True if the page appears to be a single product page, False otherwise
    """
    is_valid, _, _ = validate_product_page(content, url)
    return is_valid


# URL VALIDATION CONFIGURATION
URL_VALIDATION_CONFIG = {
    # File extensions that are NOT product pages
    "excluded_extensions": [
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.ico', '.bmp',
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt',
        # Archives
        '.zip', '.rar', '.tar', '.gz', '.7z',
        # Media
        '.mp4', '.mp3', '.avi', '.mov', '.wmv', '.flv', '.wav',
        # Web assets
        '.css', '.js', '.json', '.xml', '.rss', '.atom',
        # Executables
        '.exe', '.dmg', '.app', '.deb', '.rpm',
    ],
    
    # URL patterns that are NOT product pages
    "excluded_patterns": [
        # Navigation and listing pages
        r'/category[/-]',
        r'/categories[/-]',
        r'/collections?[/-]',
        r'/catalog[/-]',
        r'/browse[/-]',
        r'/search[\?/-]',
        r'/results[\?/-]',
        
        # Filtering and sorting
        r'/filter[/-]',
        r'/sort[/-]',
        r'/refine[/-]',
        
        # Pagination
        r'/page[/-]\d+',
        r'[?&]page=\d+',
        r'[?&]p=\d+',
        
        # Tags and taxonomies
        r'/tag[s]?[/-]',
        r'/brand[s]?[/-]',
        r'/manufacturer[s]?[/-]',
        r'/vendor[s]?[/-]',
        
        # Content pages
        r'/blog[/-]',
        r'/news[/-]',
        r'/article[s]?[/-]',
        r'/post[s]?[/-]',
        
        # Utility pages
        r'/about[/-]?$',
        r'/contact[/-]?$',
        r'/terms[/-]',
        r'/privacy[/-]',
        r'/policy[/-]',
        r'/help[/-]',
        r'/faq[/-]',
        r'/support[/-]',
        
        # Account pages
        r'/account[/-]',
        r'/profile[/-]',
        r'/login[/-]',
        r'/register[/-]',
        r'/signin[/-]',
        r'/signup[/-]',
        
        # Cart and checkout
        r'/cart[/-]?$',
        r'/basket[/-]?$',
        r'/checkout[/-]',
        r'/wishlist[/-]',
        r'/favorites[/-]',
        
        # API and system
        r'/api[/-]',
        r'/ajax[/-]',
        r'/admin[/-]',
        r'/system[/-]',
    ],
    
    # Patterns that indicate a product URL
    "product_patterns": [
        # Direct product paths
        r'/products?/[\w-]+/?$',
        r'/items?/[\w-]+/?$',
        r'/p/[\w-]+/?$',
        r'/dp/[\w-]+/?$',  # Amazon style
        r'/gp/product/[\w-]+',  # Amazon style
        
        # Product with ID patterns
        r'/listing[s]?/\d+/?$',
        r'/[\w-]+-p-\d+/?$',  # name-p-12345
        r'/[\w-]+-\d{4,}/?$',  # name-12345
        r'/product/\d{4,}/?$',
        
        # Category + product patterns (must end with product)
        r'/shop/[\w-]+/[\w-]+/?$',
        r'/store/[\w-]+/[\w-]+/?$',
        r'/[\w-]+/[\w-]+-\d+/?$',
        
        # HTML product pages
        r'/[\w-]+-\d{4,}\.html?$',
        r'/product-[\w-]+\.html?$',
        
        # E-commerce specific patterns
        r'/pd/[\w-]+',  # product detail
        r'/prd/[\w-]+',  # product
        r'/sku/[\w-]+',  # SKU based
        r'/model/[\w-]+',  # Model based
    ]
}


def is_valid_product_url(url: str, debug: bool = False) -> bool:
    """
    STRICT URL validation to check if a URL could be a product page.
    
    Args:
        url (str): URL to validate
        debug (bool): Print debug information
        
    Returns:
        bool: True if URL appears to be a valid product page
    """
    url_lower = url.lower()
    url_path = urlparse(url).path
    
    # Check 1: Exclude file extensions
    for ext in URL_VALIDATION_CONFIG["excluded_extensions"]:
        if url_lower.endswith(ext):
            if debug:
                print(f"URL rejected - file extension: {ext}")
            return False
    
    # Check 2: Exclude non-product patterns
    for pattern in URL_VALIDATION_CONFIG["excluded_patterns"]:
        if re.search(pattern, url_lower):
            if debug:
                print(f"URL rejected - excluded pattern: {pattern}")
            return False
    
    # Check 3: Look for product patterns
    for pattern in URL_VALIDATION_CONFIG["product_patterns"]:
        if re.search(pattern, url_lower):
            if debug:
                print(f"URL accepted - product pattern: {pattern}")
            return True
    
    # Check 4: Additional heuristics
    # URLs with multiple path segments ending in a slug might be products
    path_segments = [s for s in url_path.split('/') if s]
    if len(path_segments) >= 2:
        last_segment = path_segments[-1]
        # Check if last segment looks like a product slug
        if re.match(r'^[\w-]+([-_]\w+){2,}$', last_segment):
            # And contains product keywords
            product_keywords = ['product', 'item', 'buy', 'shop', 'detail', 'view']
            if any(keyword in url_lower for keyword in product_keywords):
                if debug:
                    print(f"URL accepted - product slug pattern")
                return True
    
    if debug:
        print(f"URL rejected - no matching patterns")
    
    return False


# ===============================================
# PAGINATION ENGINE UTILITIES - HYBRID APPROACH
# ===============================================

def build_session() -> requests.Session:
    """Create configured session with proper headers"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    session.timeout = 30
    return session


def double_encode(s: str) -> str:
    """Double URL encode (page=2 → page%3D2 → page%253D2)"""
    return quote(quote(s, safe=''), safe='')


def double_decode(s: str) -> str:
    """Double URL decode (page%253D2 → page%3D2 → page=2)"""
    try:
        return unquote(unquote(s))
    except:
        return s


def canonicalize_url(url: str) -> str:
    """Normalize URL by removing tracking params and standardizing"""
    try:
        parsed = urlparse(url.lower())
        
        # Remove tracking parameters
        if parsed.query:
            params = parse_qs(parsed.query, keep_blank_values=True)
            clean_params = {k: v for k, v in params.items() 
                          if not any(tracker in k.lower() for tracker in 
                                   ['utm_', 'gclid', 'fbclid', 'srsltid', '_ga', '_gid'])}
            query = '&'.join([f"{k}={''.join(v)}" for k, v in clean_params.items()])
        else:
            query = ''
        
        return urlunparse((parsed.scheme or 'https', parsed.netloc, 
                         parsed.path, parsed.params, query, ''))
    except:
        return url


def extract_pdp_links_bs4(html: str, base_url: str) -> Set[str]:
    """Extract product URLs using BeautifulSoup4 + your existing validation"""
    soup = BeautifulSoup(html, 'html.parser')
    product_urls = set()
    base_domain = urlparse(base_url).netloc
    
    # Method 1: Find anchor tags that look like product pages
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        # Convert relative URLs to absolute
        if href.startswith('/'):
            href = urljoin(base_url, href)
        elif not href.startswith(('http://', 'https://')):
            continue
        
        # Check if it's from same domain
        link_domain = urlparse(href).netloc
        if link_domain not in [base_domain, f"www.{base_domain}", base_domain.replace('www.', '')]:
            continue
        
        # Use your existing validation functions
        if is_valid_product_url(href):
            product_urls.add(canonicalize_url(href))
    
    # Method 2: JSON-LD structured data
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                if data.get('@type') == 'Product' and 'url' in data:
                    url = urljoin(base_url, data['url'])
                    if is_valid_product_url(url):
                        product_urls.add(canonicalize_url(url))
                elif data.get('@type') == 'ItemList' and 'itemListElement' in data:
                    for item in data['itemListElement']:
                        if 'url' in item:
                            url = urljoin(base_url, item['url'])
                            if is_valid_product_url(url):
                                product_urls.add(canonicalize_url(url))
        except (json.JSONDecodeError, KeyError):
            continue
    
    return product_urls


def find_next_href(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    """Find the next page link from HTML"""
    base_url = f"{urlparse(current_url).scheme}://{urlparse(current_url).netloc}"
    
    # Method 1: <link rel="next"> or <a rel="next">
    for tag in soup.find_all(['link', 'a'], rel='next'):
        if tag.get('href'):
            return urljoin(base_url, tag['href'])
    
    # Method 2: Look for "Next" text/aria/class
    next_patterns = ['next', 'older', '»', '›', '→', 'next page', 'page suivante']
    for link in soup.find_all('a', href=True):
        # Check text content
        text = (link.get_text() or '').lower().strip()
        if any(pattern in text for pattern in next_patterns):
            return urljoin(base_url, link['href'])
        
        # Check aria-label
        aria_label = (link.get('aria-label') or '').lower()
        if any(pattern in aria_label for pattern in next_patterns):
            return urljoin(base_url, link['href'])
        
        # Check class names
        classes = ' '.join(link.get('class', [])).lower()
        if any(pattern.replace(' ', '') in classes for pattern in ['next', 'nextpage']):
            return urljoin(base_url, link['href'])
    
    return None


def build_template_from_pair(url1: str, url2: str) -> Optional[Callable[[int], str]]:
    """Build URL template from page 1 and page 2 URLs"""
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)
    
    # Case 1: Pretty paths (/page/2/ or /shop/page/2/)
    if parsed1.path != parsed2.path:
        if '/page/2/' in parsed2.path or '/page/2' in parsed2.path:
            template_path = parsed2.path.replace('/page/2/', '/page/{}/').replace('/page/2', '/page/{}')
            def path_template(n):
                return f"{parsed1.scheme}://{parsed1.netloc}{template_path.format(n)}"
            return path_template
    
    # Case 2: Query parameters (?page=2 or ?paged=2)
    if parsed1.query != parsed2.query:
        params1 = parse_qs(parsed1.query, keep_blank_values=True)
        params2 = parse_qs(parsed2.query, keep_blank_values=True)
        
        for key in params2:
            if key in ['page', 'paged'] and params2[key] == ['2']:
                def query_template(n):
                    params = params1.copy()
                    params[key] = [str(n)]
                    query = '&'.join([f"{k}={''.join(v)}" for k, v in params.items()])
                    return f"{parsed1.scheme}://{parsed1.netloc}{parsed1.path}?{query}"
                return query_template
        
        # Case 3: Double-encoded store_query
        if 'store_query' in params2:
            try:
                store_query2 = double_decode(params2['store_query'][0])
                inner_params = parse_qs(store_query2, keep_blank_values=True)
                if 'page' in inner_params and inner_params['page'] == ['2']:
                    def store_query_template(n):
                        new_inner_params = inner_params.copy()
                        new_inner_params['page'] = [str(n)]
                        new_inner_query = '&'.join([f"{k}={''.join(v)}" for k, v in new_inner_params.items()])
                        encoded_query = double_encode(new_inner_query)
                        
                        params = params1.copy()
                        params['store_query'] = [encoded_query]
                        if 'store_path' not in params:
                            params['store_path'] = ['%2F']  # Default store_path
                        
                        query = '&'.join([f"{k}={''.join(v)}" for k, v in params.items()])
                        return f"{parsed1.scheme}://{parsed1.netloc}{parsed1.path}?{query}"
                    return store_query_template
            except:
                pass
    
    return None


def heuristic_templates(start_url: str) -> List[Callable[[int], str]]:
    """Generate fallback templates when no Next link found"""
    parsed = urlparse(start_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    templates = []
    
    # Template 1: Pretty path /page/{n}/
    templates.append(lambda n: f"{base_url.rstrip('/')}/page/{n}/")
    
    # Template 2: Query ?page={n}
    if parsed.query:
        templates.append(lambda n: f"{base_url}?{parsed.query}&page={n}")
    else:
        templates.append(lambda n: f"{base_url}?page={n}")
    
    # Template 3: Query ?paged={n}
    if parsed.query:
        templates.append(lambda n: f"{base_url}?{parsed.query}&paged={n}")
    else:
        templates.append(lambda n: f"{base_url}?paged={n}")
    
    # Template 4: Double-encoded store_query
    def store_query_template(n):
        inner_query = f"page={n}"
        encoded_query = double_encode(inner_query)
        if parsed.query:
            return f"{base_url}?{parsed.query}&store_query={encoded_query}&store_path=%2F"
        else:
            return f"{base_url}?store_query={encoded_query}&store_path=%2F"
    templates.append(store_query_template)
    
    return templates


def crawl_listing_pagination(start_url: str, max_pages: int = 20, delay: float = 0.6, timeout: int = 30, verbose: bool = True) -> Tuple[List[str], Set[str]]:
    """
    MAIN PAGINATION CRAWLER - Smart pagination detection and crawling
    
    Returns:
        Tuple[List[str], Set[str]]: (visited_page_urls, all_product_urls)
    """
    session = build_session()
    visited_pages = []
    all_product_urls = set()
    page_content_hashes = set()
    
    if verbose:
        print(f"Starting pagination crawl of: {start_url}")
        print(f"Max pages: {max_pages}, Delay: {delay}s")
    
    # Step 1: Fetch page 1
    try:
        if verbose:
            print(f"\n[Page 1] Fetching {start_url}")
        
        response = session.get(start_url, timeout=timeout)
        response.raise_for_status()
        
        page1_html = response.text
        page1_hash = hashlib.md5(page1_html.encode()).hexdigest()
        page_content_hashes.add(page1_hash)
        visited_pages.append(start_url)
        
        # Extract products from page 1
        soup1 = BeautifulSoup(page1_html, 'html.parser')
        page1_products = extract_pdp_links_bs4(page1_html, start_url)
        all_product_urls.update(page1_products)
        
        if verbose:
            print(f"[Page 1] Found {len(page1_products)} product URLs")
        
        time.sleep(delay)
        
    except Exception as e:
        if verbose:
            print(f"[Page 1] Error: {e}")
        return visited_pages, all_product_urls
    
    # Step 2: Try to find Next link and build template
    url_template = None
    next_url = find_next_href(soup1, start_url)
    
    if next_url and next_url != start_url:
        if verbose:
            print(f"[Template] Found Next link: {next_url}")
        
        # Try to fetch page 2 to build template
        try:
            response2 = session.get(next_url, timeout=timeout)
            response2.raise_for_status()
            
            # Build template from page 1 and page 2
            template = build_template_from_pair(start_url, next_url)
            if template:
                url_template = template
                if verbose:
                    print(f"[Template] Built pagination template from Next link")
            
            time.sleep(delay)
        except Exception as e:
            if verbose:
                print(f"[Template] Error testing Next link: {e}")
    
    # Step 3: Fallback to heuristic templates if no Next found
    if not url_template:
        if verbose:
            print(f"[Template] No Next link found, trying heuristic templates")
        heuristic_temps = heuristic_templates(start_url)
        
        # Test each heuristic template
        for i, template in enumerate(heuristic_temps):
            try:
                test_url = template(2)
                if verbose:
                    print(f"[Template] Testing heuristic {i+1}: {test_url}")
                
                response = session.get(test_url, timeout=timeout)
                response.raise_for_status()
                
                # Check if page 2 content is different from page 1
                page2_html = response.text
                page2_hash = hashlib.md5(page2_html.encode()).hexdigest()
                
                if page2_hash != page1_hash:
                    # Test if it has products
                    page2_products = extract_pdp_links_bs4(page2_html, test_url)
                    if page2_products and not page2_products.issubset(page1_products):
                        url_template = template
                        if verbose:
                            print(f"[Template] Heuristic {i+1} worked! Found {len(page2_products)} new products")
                        break
                
                time.sleep(delay)
                
            except Exception as e:
                if verbose:
                    print(f"[Template] Heuristic {i+1} failed: {e}")
                continue
    
    # Step 4: Crawl remaining pages using template
    if url_template:
        for page_num in range(2, max_pages + 1):
            try:
                page_url = url_template(page_num)
                
                if verbose:
                    print(f"\n[Page {page_num}] Fetching {page_url}")
                
                # Skip if URL equals current or previous
                if page_url in visited_pages:
                    if verbose:
                        print(f"[Page {page_num}] Duplicate URL, stopping")
                    break
                
                response = session.get(page_url, timeout=timeout)
                response.raise_for_status()
                
                # Check for content repetition
                page_html = response.text
                page_hash = hashlib.md5(page_html.encode()).hexdigest()
                
                if page_hash in page_content_hashes:
                    if verbose:
                        print(f"[Page {page_num}] Content hash repeated, stopping")
                    break
                
                page_content_hashes.add(page_hash)
                visited_pages.append(page_url)
                
                # Extract products
                page_products = extract_pdp_links_bs4(page_html, page_url)
                
                if not page_products:
                    if verbose:
                        print(f"[Page {page_num}] No products found, stopping")
                    break
                
                new_products = page_products - all_product_urls
                all_product_urls.update(page_products)
                
                if verbose:
                    print(f"[Page {page_num}] Found {len(page_products)} products ({len(new_products)} new)")
                
                # Stop if no new products found
                if not new_products:
                    if verbose:
                        print(f"[Page {page_num}] No new products, stopping")
                    break
                
                time.sleep(delay)
                
            except Exception as e:
                if verbose:
                    print(f"[Page {page_num}] Error: {e}")
                break
    else:
        if verbose:
            print("[Template] No working pagination template found")
    
    session.close()
    
    if verbose:
        print(f"\n[Complete] Crawled {len(visited_pages)} pages, found {len(all_product_urls)} total product URLs")
    
    return visited_pages, all_product_urls


def get_crawl_limits():
    """Get user preferences for crawling limits"""
    print("\nCrawling Options:")
    print("1. Limit by PAGES (e.g., crawl only 3 pages)")
    print("2. Limit by PRODUCTS (e.g., stop after 25 products)")  
    print("3. Crawl ALL pages until no more found")
    
    while True:
        choice = input("\nChoose option (1/2/3): ").strip()
        
        if choice == "1":
            while True:
                try:
                    pages = int(input("How many pages to crawl? "))
                    if pages > 0:
                        return {"type": "pages", "limit": pages}
                    else:
                        print("Please enter a number greater than 0")
                except ValueError:
                    print("Please enter a valid number")
        
        elif choice == "2":
            while True:
                try:
                    products = int(input("How many products maximum? "))
                    if products > 0:
                        return {"type": "products", "limit": products}
                    else:
                        print("Please enter a number greater than 0")
                except ValueError:
                    print("Please enter a valid number")
                    
        elif choice == "3":
            return {"type": "all", "limit": 999}  # High number for max pages
            
        else:
            print("Please choose 1, 2, or 3")


def crawl_with_playwright(start_url: str, limits: dict = None, delay: float = 2.0, verbose: bool = True) -> Set[str]:
    """
    PLAYWRIGHT CRAWLER - Simple and focused with detailed debugging
    Opens browser, clicks through pagination, extracts product URLs
    """
    if not PLAYWRIGHT_AVAILABLE:
        print("ERROR: Playwright not available. Run: pip install playwright && playwright install chromium")
        return set()
    
    # Set default limits if not provided
    if limits is None:
        limits = {"type": "all", "limit": 999}
    
    all_product_urls = set()
    max_pages = limits["limit"] if limits["type"] == "pages" else 999
    max_products = limits["limit"] if limits["type"] == "products" else 999999
    
    print(f"\n🎯 Crawling with {limits['type']} limit: {limits['limit']}")
    print("=" * 50)
    
    try:
        print(f"🚀 Starting Playwright browser automation...")
        with sync_playwright() as p:
            if is_debug_enabled():
                print(f"DEBUG: Playwright context created successfully")
            
            # Test browser launch
            try:
                if is_debug_enabled():
                    print(f"DEBUG: Launching Chromium browser...")
                browser = p.chromium.launch(
                    headless=False,  # Show browser for debugging
                    args=['--no-sandbox', '--disable-web-security', '--disable-dev-shm-usage']
                )
                if is_debug_enabled():
                    print(f"DEBUG: Browser launched successfully")
            except Exception as launch_error:
                print(f"ERROR: Failed to launch browser: {launch_error}")
                return set()
            
            # Test page creation
            try:
                if is_debug_enabled():
                    print(f"DEBUG: Creating new page...")
                page = browser.new_page()
                page.set_viewport_size({"width": 1280, "height": 720})
                if is_debug_enabled():
                    print(f"DEBUG: Page created successfully")
            except Exception as page_error:
                print(f"ERROR: Failed to create page: {page_error}")
                browser.close()
                return set()
            
            # Test navigation
            try:
                if is_debug_enabled():
                    print(f"DEBUG: Navigating to {start_url}...")
                response = page.goto(start_url, timeout=60000, wait_until='domcontentloaded')  # Back to faster loading
                if is_debug_enabled():
                    print(f"DEBUG: Navigation response status: {response.status if response else 'None'}")
                
                # Quick wait for essential content
                if is_debug_enabled():
                    print(f"DEBUG: Waiting for essential content...")
                page.wait_for_timeout(3000)  # 3 seconds only
                
                # Check if page loaded
                title = page.title()
                if is_debug_enabled():
                    print(f"DEBUG: Page title: '{title}'")
                
            except Exception as nav_error:
                print(f"ERROR: Failed to navigate to page: {nav_error}")
                browser.close()
                return set()
            
            # Test link extraction
            try:
                if is_debug_enabled():
                    print(f"DEBUG: Extracting product links from page 1...")
                page1_urls = get_product_links_simple(page, start_url)
                
                # Apply product limit to page 1 as well
                if limits["type"] == "products":
                    page1_urls_limited = list(page1_urls)[:max_products]
                    all_product_urls.update(page1_urls_limited)
                    if is_debug_enabled():
                        print(f"DEBUG: Page 1 found {len(page1_urls)} URLs, added {len(page1_urls_limited)} (limit: {max_products})")
                        print(f"DEBUG: Total products: {len(all_product_urls)}/{max_products}")
                    
                    # Check if page 1 already satisfies the limit
                    if len(all_product_urls) >= max_products:
                        if is_debug_enabled():
                            print(f"DEBUG: Reached product limit ({max_products}) on page 1, stopping")
                        browser.close()
                        return all_product_urls
                else:
                    all_product_urls.update(page1_urls)
                    if is_debug_enabled():
                        print(f"DEBUG: Page 1 extracted {len(page1_urls)} product URLs")
                
                # Show first few URLs for debugging
                if page1_urls:
                    if is_debug_enabled():
                        print(f"DEBUG: First few URLs: {list(page1_urls)[:3]}")
                
            except Exception as extract_error:
                print(f"ERROR: Failed to extract links: {extract_error}")
                browser.close()
                return all_product_urls
            
            # Test pagination
            try:
                if is_debug_enabled():
                    print(f"DEBUG: Looking for pagination links...")
                
                # Check for various pagination patterns
                pagination_selectors = [
                    'a:has-text("2")',
                    'a:has-text("Next")', 
                    'a[aria-label*="page 2"]',
                    '.pagination a',
                    '.pager a',
                    'a[href*="page=2"]',
                    'a[href*="page/2"]'
                ]
                
                found_pagination = False
                for selector in pagination_selectors:
                    try:
                        elements = page.locator(selector).all()
                        if elements:
                            if is_debug_enabled():
                                print(f"DEBUG: Found {len(elements)} elements with selector '{selector}'")
                            found_pagination = True
                            break
                    except:
                        continue
                
                if not found_pagination:
                    if is_debug_enabled():
                        print(f"DEBUG: No pagination elements found, checking page source for pagination indicators")
                    page_content = page.content()
                    pagination_indicators = ['page 2', 'next page', 'pagination', 'page-item']
                    for indicator in pagination_indicators:
                        if indicator.lower() in page_content.lower():
                            if is_debug_enabled():
                                print(f"DEBUG: Found pagination indicator '{indicator}' in page source")
                            break
                    else:
                        if is_debug_enabled():
                            print(f"DEBUG: No pagination indicators found in page source")
                
                # Try to find and click through pages
                for page_num in range(2, max_pages + 1):
                    # Check product limit
                    if limits["type"] == "products" and len(all_product_urls) >= max_products:
                        if is_debug_enabled():
                            print(f"DEBUG: Reached product limit ({max_products}), stopping")
                        break
                    if is_debug_enabled():
                        print(f"DEBUG: Looking for page {page_num}...")
                    
                    # Try different strategies to find page link
                    page_link = None
                    strategies = [
                        f'a:has-text("{page_num}")',
                        f'a[href*="page={page_num}"]',
                        f'a[href*="page/{page_num}"]',
                        f'a[aria-label*="page {page_num}"]'
                    ]
                    
                    for strategy in strategies:
                        try:
                            locator = page.locator(strategy).first
                            if locator.is_visible(timeout=3000):  # 3 seconds to find pagination
                                page_link = locator
                                if is_debug_enabled():
                                    print(f"DEBUG: Found page {page_num} link using strategy: {strategy}")
                                break
                        except:
                            continue
                    
                    if page_link:
                        try:
                            if is_debug_enabled():
                                print(f"DEBUG: Clicking page {page_num} link...")
                            page_link.click()
                            
                            # Quick wait for navigation
                            try:
                                page.wait_for_load_state('domcontentloaded', timeout=10000)  # Just wait for DOM
                            except:
                                pass  # Continue even if it times out
                            
                            page.wait_for_timeout(2000)  # Quick 2 second wait
                            
                            # Verify navigation worked
                            current_url = page.url
                            if is_debug_enabled():
                                print(f"DEBUG: Current URL after click: {current_url}")
                            
                            # Get products from this page
                            page_urls = get_product_links_simple(page, page.url)
                            new_urls = page_urls - all_product_urls
                            
                            # If we have a product limit, only add what we need
                            if limits["type"] == "products":
                                remaining_needed = max_products - len(all_product_urls)
                                if remaining_needed <= 0:
                                    if is_debug_enabled():
                                        print(f"DEBUG: Already at product limit ({max_products}), stopping")
                                    break
                                
                                # Only add up to the limit
                                new_urls_limited = list(new_urls)[:remaining_needed]
                                all_product_urls.update(new_urls_limited)
                                
                                if is_debug_enabled():
                                    print(f"DEBUG: Page {page_num} found {len(page_urls)} URLs, added {len(new_urls_limited)} (limit: {max_products})")
                                    print(f"DEBUG: Total products: {len(all_product_urls)}/{max_products}")
                                
                                # Check if we've hit the exact limit
                                if len(all_product_urls) >= max_products:
                                    if is_debug_enabled():
                                        print(f"DEBUG: Reached exact product limit ({max_products}), stopping")
                                    break
                            else:
                                # No product limit, add all
                                all_product_urls.update(page_urls)
                                if is_debug_enabled():
                                    print(f"DEBUG: Page {page_num} extracted {len(page_urls)} URLs ({len(new_urls)} new)")
                                    print(f"DEBUG: Total products so far: {len(all_product_urls)}")
                            
                            if not new_urls:
                                if is_debug_enabled():
                                    print(f"DEBUG: No new products found, stopping pagination")
                                break
                                
                            page.wait_for_timeout(int(delay * 1000))
                            
                        except Exception as click_error:
                            print(f"ERROR: Failed to click page {page_num}: {click_error}")
                            break
                    else:
                        if is_debug_enabled():
                            print(f"DEBUG: No page {page_num} link found, stopping pagination")
                        break
                        
            except Exception as pagination_error:
                print(f"ERROR: Pagination failed: {pagination_error}")
            
            # Close browser
            try:
                if is_debug_enabled():
                    print(f"DEBUG: Closing browser...")
                browser.close()
                if is_debug_enabled():
                    print(f"DEBUG: Browser closed successfully")
            except Exception as close_error:
                print(f"WARNING: Error closing browser: {close_error}")
            
    except Exception as e:
        print(f"CRITICAL ERROR: Playwright failed completely: {e}")
        import traceback
        if is_debug_enabled():
            print(f"DEBUG: Full traceback:")
        traceback.print_exc()
        return all_product_urls
    
    print(f"SUCCESS: Playwright completed with {len(all_product_urls)} total URLs")
    return all_product_urls


def is_product_link_semantic(link_element, href: str, base_domain: str) -> bool:
    """Universal semantic detection of product links across all e-commerce platforms"""
    try:
        # Quick domain check
        if base_domain not in href:
            return False
            
        # Universal exclusion patterns (works on ALL sites) - CONSERVATIVE APPROACH
        exclusion_patterns = [
            # Navigation & Categories
            r'/category/', r'/categories/', r'/collection/', r'/collections/',
            r'/catalog/', r'/browse/', r'/search/', r'/results/',
            
            # Filters & Sorting  
            r'/filter/', r'/sort/', r'/refine/', r'\?sort=', r'\?filter=',
            r'\?page=', r'\?p=', r'\?category=',
            
            # Content Pages
            r'/blog/', r'/news/', r'/article/', r'/post/', r'/guide/',
            r'/about/', r'/contact/', r'/help/', r'/support/', r'/faq/',
            
            # Account & System
            r'/account/', r'/login/', r'/register/', r'/checkout/',
            r'/cart/', r'/basket/', r'/wishlist/', r'/compare/',
            r'/api/', r'/admin/', r'/system/',
            
            # Media & Files
            r'\.(jpg|png|gif|pdf|css|js)$',
            
            # Only block very specific problematic patterns
            r'/list/shop-all-gifts/',  # Only the specific gift category
            r'argos\.co\.uk/$'  # Only Argos homepage specifically
        ]
        
        # Check if URL matches exclusion patterns
        for pattern in exclusion_patterns:
            if re.search(pattern, href.lower()):
                return False
        
        # Get link context (parent elements and surrounding text)
        try:
            # Check link text and attributes
            link_text = link_element.inner_text().lower().strip()
            link_title = (link_element.get_attribute('title') or '').lower()
            link_aria = (link_element.get_attribute('aria-label') or '').lower()
            
            # Get immediate parent for context (not global elements)
            parent = link_element.locator('xpath=..').first
            parent_class = (parent.get_attribute('class') or '').lower()
            
            # Only get limited parent HTML to avoid global cart buttons
            try:
                parent_html = parent.inner_html()[:200].lower()  # Very limited to avoid global elements
            except:
                parent_html = ''
            
            # Skip if this looks like a global/persistent element
            global_indicators = ['header', 'nav', 'footer', 'sidebar', 'fixed', 'sticky', 'persistent']
            if any(indicator in parent_class for indicator in global_indicators):
                return False
            
        except:
            # If we can't get context, fall back to URL analysis
            link_text = link_title = link_aria = parent_class = parent_html = ''
        
        # Universal product indicators in LOCAL context (not global elements)
        product_indicators = [
            # Specific price indicators (with context)
            r'£\d+[\.\d]*', r'\$\d+[\.\d]*', r'€\d+[\.\d]*', 
            r'price:\s*£', r'price:\s*\$', r'from\s+£\d+', r'from\s+\$\d+',
            
            # Product-specific actions (not generic cart buttons)
            r'quick view', r'view product', r'product details', r'more info',
            r'view item', r'see product', r'shop this', r'buy this',
            
            # Product-specific elements
            r'product', r'item', r'sku', r'model', r'brand',
            r'rating', r'review', r'\d+\s*star', r'in stock', r'out of stock',
            
            # Product container context (specific to product listings)
            r'product-card', r'item-card', r'product-tile', r'product-item',
            r'shop-item', r'listing-item', r'grid-item', r'product-box',
            
            # Image indicators (products often have images)
            r'product-image', r'item-image', r'product-photo'
        ]
        
        # Exclude if it's clearly a global/navigation element
        global_exclusions = [
            r'main-nav', r'header', r'footer', r'sidebar', r'menu',
            r'cart-icon', r'cart-button', r'shopping-cart', r'mini-cart',
            r'search', r'login', r'account', r'wishlist-icon'
        ]
        
        # Check if any product indicators are present
        context_text = f"{link_text} {link_title} {link_aria} {parent_class} {parent_html}"
        
        # First check for global exclusions (skip persistent cart buttons etc)
        for exclusion in global_exclusions:
            if re.search(exclusion, context_text):
                return False
        
        # Then look for product indicators
        for indicator in product_indicators:
            if re.search(indicator, context_text):
                return True
        
        # Universal product URL patterns (final check)
        product_url_patterns = [
            r'/product[s]?/[\w-]+/?$',  # /products/item-name
            r'/item[s]?/[\w-]+/?$',     # /items/item-name  
            r'/p/[\w-]+/?$',            # /p/item-name
            r'/[\w-]+-p-\d+/?$',        # name-p-12345
            r'/product/\d+/?$',         # /product/12345 (Argos style)
            r'/dp/[\w\d]+/?$',          # /dp/B08ABC123 (Amazon style)
            r'/[\w-]+\.html?$',         # item-name.html
        ]
        
        for pattern in product_url_patterns:
            if re.search(pattern, href):
                return True
                
        return False
        
    except Exception as e:
        # If semantic analysis fails, be conservative
        return False


def get_product_links_semantic(page, base_url: str) -> Set[str]:
    """Universal semantic product link extraction - works on ALL e-commerce platforms"""
    product_urls = set()
    base_domain = urlparse(base_url).netloc.replace('www.', '')
    
    try:
        print(f"\n📝 Getting all links with semantic analysis...")
        
        # First, wait a bit more if the page seems to still be loading products
        try:
            # Check if there are loading indicators or if product count is increasing
            page.wait_for_function("document.querySelectorAll('a[href]').length > 10", timeout=5000)
        except:
            pass  # Continue even if this fails
        
        links = page.locator('a[href]').all()
        print(f"📊 Found {len(links)} total links to analyze\n")
        
        valid_urls = 0
        analyzed_count = 0
        
        for i, link in enumerate(links):
            try:
                href = link.get_attribute('href')
                if not href:
                    continue
                    
                analyzed_count += 1
                
                # Show progress every 100 links (with clean spacing)
                if analyzed_count % 100 == 0:
                    print(f"\n[PROGRESS] {analyzed_count}/{len(links)} links analyzed | {valid_urls} products found\n")
                
                # Make absolute URL
                if href.startswith('/'):
                    full_url = urljoin(base_url, href)
                elif href.startswith(('http://', 'https://')):
                    full_url = href
                else:
                    continue
                
                # Universal semantic validation
                if is_product_link_semantic(link, full_url, base_domain):
                    product_urls.add(canonicalize_url(full_url))
                    valid_urls += 1
                    
                    # Show first few valid URLs for debugging
                    if valid_urls <= 3:
                        if is_debug_enabled():
                            print(f"DEBUG: Valid product URL #{valid_urls}: {full_url}")
                    
            except Exception as link_error:
                if i < 5:  # Only show first few link errors
                    if is_debug_enabled():
                        print(f"DEBUG: Error analyzing link {i}: {link_error}")
                continue
                
        print(f"\n✅ Analysis complete: {analyzed_count} links analyzed → {len(product_urls)} valid product URLs found\n")
        
    except Exception as e:
        print(f"ERROR: Failed to get semantic links: {e}")
        import traceback
        traceback.print_exc()
    
    return product_urls


# Keep the old function as backup
def get_product_links_simple(page, base_url: str) -> Set[str]:
    """Simple product link extraction - BACKUP METHOD"""  
    return get_product_links_semantic(page, base_url)


def extract_product_urls_from_page(page: 'Page', base_url: str, verbose: bool = False) -> Set[str]:
    """Extract product URLs from a Playwright page"""
    if not PLAYWRIGHT_AVAILABLE:
        return set()
    
    product_urls = set()
    
    try:
        # Use scoped product link extraction from pdp_filters
        from pdp_filters import scoped_product_links_from_page
        scoped_urls = scoped_product_links_from_page(page, base_url)
        
        if scoped_urls:
            print(f"    Found {len(scoped_urls)} scoped product URLs")
            product_urls.update(scoped_urls)
        else:
            # Fallback to old method if scoped extraction finds nothing
            print("    Scoped extraction found nothing, falling back to general link scan...")
            links = page.locator('a[href]').all()
            
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if not href:
                        continue
                    
                    # Convert relative to absolute URL
                    if href.startswith('/'):
                        full_url = urljoin(base_url, href)
                    elif href.startswith(('http://', 'https://')):
                        full_url = href
                    else:
                        continue
                    
                    # Use new validation from pdp_filters
                    from pdp_filters import is_candidate_product_url, canonicalize_url as pdp_canonicalize
                    base_netloc = urlparse(base_url).netloc
                    if is_candidate_product_url(full_url, base_netloc):
                        product_urls.add(pdp_canonicalize(full_url))
                        
                except:
                    continue
                
    except Exception as e:
        if verbose:
            print(f"Error extracting URLs from page: {e}")
    
    return product_urls


def extract_product_urls(content: str, base_url: str) -> List[str]:
    """
    Extract product URLs from page content.
    
    Args:
        content (str): Page content to analyze
        base_url (str): Base URL for the website
        
    Returns:
        List[str]: List of product URLs found
    """
    urls: List[str] = []
    base_domain = urlparse(base_url).netloc
    
    # Handle both www and non-www versions
    base_domain_parts = base_domain.split('.')
    if base_domain_parts[0] == 'www':
        alt_domain = '.'.join(base_domain_parts[1:])
    else:
        alt_domain = 'www.' + base_domain
    
    # Find all URLs in markdown links (excluding any title attributes)
    markdown_urls = re.findall(r'\[.*?\]\((https?://[^\s\)\"]+)', content)
    # Find plain URLs
    plain_urls = re.findall(r'https?://[^\s<>"\[\]\)]+', content)
    
    all_urls = set(markdown_urls + plain_urls)
    
    for url in all_urls:
        # Clean URL
        url = url.strip().rstrip('.,;:!?')
        
        # Check if URL is from same domain (with or without www)
        url_domain = urlparse(url).netloc
        if url_domain == base_domain or url_domain == alt_domain:
            # Check if it's a valid product URL
            if is_valid_product_url(url):
                urls.append(url)
    
    return urls


def detect_site_structure(app: firecrawl.FirecrawlApp, start_url: str) -> Dict[str, Any]:
    """Detect the site structure and navigation patterns"""
    structure = {
        "platform": "unknown",
        "has_pagination": False,
        "category_pages": [],
        "shop_pages": [],
        "navigation_patterns": []
    }
    
    spinner = DotSpinner("Analyzing site structure")
    spinner.start()
    
    try:
        # Get homepage content to analyze structure
        result = app.extract(
            [start_url],
            prompt="""Analyze this e-commerce site structure and return:
            1. Platform type (Shopify, WooCommerce, Custom, etc.)
            2. Main navigation links to shop/category pages
            3. Any pagination indicators
            4. Site structure patterns""",
            schema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "shop_links": {"type": "array", "items": {"type": "string"}},
                    "has_pagination": {"type": "boolean"},
                    "navigation_structure": {"type": "string"}
                }
            }
        )
        
        if result and hasattr(result, 'data') and result.data:
            data = result.data[0] if isinstance(result.data, list) else result.data
            structure.update({
                "platform": data.get("platform", "unknown"),
                "has_pagination": data.get("has_pagination", False),
                "shop_pages": data.get("shop_links", [])
            })
    except Exception:
        pass  # Continue with defaults
    finally:
        spinner.stop()
    
    return structure


def crawl_all_pages(app: firecrawl.FirecrawlApp, start_url: str) -> Set[str]:
    """
    Enhanced crawler that finds ALL product URLs across the entire site
    """
    product_urls: Set[str] = set()
    pages_to_crawl: List[str] = [start_url]
    crawled_pages: Set[str] = set()
    
    print(f"Analyzing site structure...")
    site_info = detect_site_structure(app, start_url)
    print(f"   Platform: {site_info['platform']}")
    print(f"   Pagination: {site_info['has_pagination']}")
    print(f"   Shop pages found: {len(site_info['shop_pages'])}")
    
    # Add shop/category pages to crawl list
    pages_to_crawl.extend(site_info['shop_pages'][:10])  # Limit to 10 category pages
    
    print(f"\nCrawling {len(pages_to_crawl)} pages for product URLs...")
    
    for page_url in tqdm(pages_to_crawl, desc="Crawling pages"):
        if page_url in crawled_pages:
            continue
        
        try:
            # Start spinner for this page
            page_name = page_url.split('/')[-1] or 'homepage'
            spinner = DotSpinner(f"Extracting links from {page_name}")
            spinner.start()
            
            try:
                # Extract all links from this page
                result = app.extract(
                    [page_url],
                    prompt="""Extract ALL internal links from this page that could be:
                    1. Direct product pages
                    2. Category/collection pages with more products
                    3. Pagination links (Next page, Page 2, etc.)
                    
                    Focus on e-commerce links, exclude utility pages.""",
                    schema={
                        "type": "object",
                        "properties": {
                            "product_links": {"type": "array", "items": {"type": "string"}},
                            "category_links": {"type": "array", "items": {"type": "string"}},
                            "pagination_links": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                )
            finally:
                spinner.stop()
            
            if result and hasattr(result, 'data') and result.data:
                data = result.data[0] if isinstance(result.data, list) else result.data
                
                # Add product URLs
                for url in data.get('product_links', []):
                    if is_valid_product_url(url):
                        product_urls.add(url)
                
                # Add category pages for further crawling (limited to prevent infinite loops)
                if len(pages_to_crawl) < 25:  # Max 25 total pages
                    for url in data.get('category_links', [])[:5]:  # Max 5 new categories per page
                        if url not in crawled_pages and url not in pages_to_crawl:
                            pages_to_crawl.append(url)
                    
                    for url in data.get('pagination_links', [])[:3]:  # Max 3 pagination links
                        if url not in crawled_pages and url not in pages_to_crawl:
                            pages_to_crawl.append(url)
            
            crawled_pages.add(page_url)
            time.sleep(0.2)  # Small delay between pages
            
        except Exception as e:
            print(f"\nError crawling {page_url}: {e}")
            crawled_pages.add(page_url)  # Mark as crawled to avoid retry
            continue
    
    print(f"\nCrawling complete!")
    print(f"   Pages crawled: {len(crawled_pages)}")
    print(f"   Product URLs found: {len(product_urls)}")
    
    return product_urls


def scrape_static_html_urls(start_url: str) -> Set[str]:
    """
    Fast static HTML scraping without JavaScript execution.
    Perfect for sites with simple HTML structure and pagination.
    Expected time: 5-15 seconds
    """
    import requests
    from bs4 import BeautifulSoup
    import time
    
    found_urls = set()
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Try common product listing pages first
        base_domain = urlparse(start_url).netloc
        potential_pages = [
            start_url,
            f"https://{base_domain}/products",
            f"https://{base_domain}/shop", 
            f"https://{base_domain}/catalog",
            f"https://{base_domain}/collections/all"
        ]
        
        start_time = time.time()
        
        for page_url in potential_pages:
            if time.time() - start_time > 15:  # 15 second timeout
                print("⏰ Static HTML timeout reached")
                break
                
            try:
                response = requests.get(page_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Look for product links using multiple strategies
                    product_links = set()
                    
                    # Strategy 1: Common product URL patterns
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        if any(pattern in href.lower() for pattern in ['/product', '/item', '/p/', 'products/']):
                            if href.startswith('/'):
                                href = f"https://{base_domain}{href}"
                            elif href.startswith('http'):
                                pass  # Already full URL
                            else:
                                continue
                            product_links.add(href)
                    
                    # Strategy 2: Look for pagination to find more pages
                    pagination_links = soup.find_all('a', href=True)
                    page_urls = []
                    for link in pagination_links:
                        href = link['href']
                        text = link.get_text().lower().strip()
                        if any(word in text for word in ['next', '2', '3', '4', '5', 'page']):
                            if 'page=' in href or '/page/' in href:
                                if href.startswith('/'):
                                    href = f"https://{base_domain}{href}"
                                page_urls.append(href)
                    
                    # Quick scan of first few pagination pages (max 3)
                    for i, page_url in enumerate(page_urls[:3]):
                        if time.time() - start_time > 12:  # Leave 3 seconds buffer
                            break
                        try:
                            page_response = requests.get(page_url, headers=headers, timeout=5)
                            if page_response.status_code == 200:
                                page_soup = BeautifulSoup(page_response.content, 'html.parser')
                                for link in page_soup.find_all('a', href=True):
                                    href = link['href']
                                    if any(pattern in href.lower() for pattern in ['/product', '/item', '/p/']):
                                        if href.startswith('/'):
                                            href = f"https://{base_domain}{href}"
                                        product_links.add(href)
                        except:
                            continue
                    
                    # Validate and add found links
                    for url in product_links:
                        if is_candidate_product_url(url, base_domain):
                            found_urls.add(canonicalize_url(url))
                    
                    if len(product_links) > 5:  # Found good results on this page
                        break
                        
            except Exception as e:
                continue
        
        return found_urls
        
    except Exception as e:
        print(f"Static HTML error: {e}")
        return set()


def check_site_compatibility(start_url: str) -> tuple[bool, str]:
    """
    Check if a site has problematic layouts that could break scraping.
    Returns (is_compatible, reason_if_incompatible)
    """
    import requests
    from bs4 import BeautifulSoup
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(start_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return False, f"Site returned status {response.status_code}"
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for problematic patterns
        page_text = soup.get_text().lower()
        
        # Pattern 1: Sites that show product details with product listings mixed
        if "product details" in page_text or "product info" in page_text:
            product_links = soup.find_all('a', href=True)
            product_count = len([link for link in product_links 
                               if any(pattern in link.get('href', '').lower() 
                                     for pattern in ['/product', '/item', '/p/'])])
            
            if product_count > 10:  # Too many product links on a product page = mixed layout
                return False, "Site has mixed product listing/detail layout - causes duplicate extraction"
        
        # Pattern 2: Sites requiring login for product access
        if any(phrase in page_text for phrase in ["please log in", "sign in to view", "login required", "member only"]):
            return False, "Site requires login/membership to view products"
        
        # Pattern 3: Sites with broken pagination or infinite scroll issues
        if "loading" in page_text and "scroll" in page_text and len(page_text) < 1000:
            return False, "Site appears to use problematic infinite scroll implementation"
        
        # Pattern 4: Sites with CAPTCHA or bot protection
        if any(phrase in page_text for phrase in ["captcha", "verify you are human", "cloudflare"]):
            return False, "Site has bot protection that interferes with scraping"
        
        return True, ""
        
    except Exception as e:
        return False, f"Unable to analyze site compatibility: {str(e)[:100]}"


def scrape_product_pages(start_url: str) -> Set[str]:
    """
    Hybrid Product URL Extraction with Smart Detection (4-Method Approach)
    
    1. COMPATIBILITY CHECK - Detect problematic layouts
    2. SITEMAP Discovery (2 seconds) - XML sitemaps for instant URL lists
    3. STATIC HTML Scraping (5-15 seconds) - Simple HTTP requests + parsing  
    4. FIRECRAWL API (30-60 seconds) - Cloud scraping for JS-heavy sites
    5. PLAYWRIGHT Browser (60+ seconds) - Full browser automation for complex sites
    """
    print(f"🕷️ HYBRID SCRAPER: Product URL Extraction")
    print(f"Target: {start_url}")
    
    # STEP 0: Check site compatibility first (if enabled in settings)
    from scraper import load_settings
    settings = load_settings()
    
    if settings.get('site_compatibility', {}).get('enabled', True):
        print("🔍 [0/4] COMPATIBILITY: Analyzing site layout...")
        is_compatible, incompatibility_reason = check_site_compatibility(start_url)
        
        if not is_compatible:
            print(f"❌ SITE INCOMPATIBLE: {incompatibility_reason}")
            print("🚫 This site has a problematic layout that would cause issues:")
            print("   • Mixed product listings and details on same pages")
            print("   • Login requirements or bot protection") 
            print("   • Broken pagination or infinite scroll")
            print("")
            print("💡 RECOMMENDATION: Skip this site or manually provide specific product URLs")
            print("   The scraper is designed to work reliably - this site would break that reliability.")
            print("")
            
            # Check if auto-skip is enabled
            auto_skip = settings.get('site_compatibility', {}).get('auto_skip_incompatible', True)
            
            if auto_skip:
                print("✅ Auto-skipping incompatible site (configured in settings.json)")
                return set()
            else:
                # Ask user if they want to proceed anyway
                try:
                    user_choice = input("⚠️  Proceed anyway? This may cause duplicate/invalid data (y/N): ").strip().lower()
                    if user_choice not in ['y', 'yes']:
                        print("✅ Skipping incompatible site - scraper reliability maintained")
                        return set()
                    else:
                        print("⚠️  Proceeding with incompatible site - expect issues...")
                except:
                    # If running in non-interactive mode, skip automatically
                    print("✅ Auto-skipping incompatible site (non-interactive mode)")
                    return set()
        else:
            print("✅ Site appears compatible with scraping")
    else:
        print("⏭️  Site compatibility checking disabled")
    
    all_urls = set()  # Collect URLs from all successful methods
    
    # METHOD 1: Try sitemap extraction first (2 seconds = JACKPOT!)
    print("🚀 [1/4] SITEMAP: Checking for XML sitemaps...")
    try:
        sitemap_urls = sitemap_pdp_urls(start_url)
        if len(sitemap_urls) >= 10:  # Substantial amount found
            print(f"🚀 JACKPOT! Sitemap found {len(sitemap_urls)} product URLs in ~2 seconds")
            print("✅ Sitemap method sufficient - skipping other methods")
            save_urls_to_file(sitemap_urls)
            return sitemap_urls
        elif len(sitemap_urls) >= 3:
            print(f"⚠️ Sitemap found {len(sitemap_urls)} URLs (will supplement with other methods)")
            all_urls.update(sitemap_urls)
        else:
            print("📭 No useful product sitemap found")
    except Exception as e:
        print(f"❌ Sitemap extraction failed: {str(e)[:100]}...")
        sitemap_urls = set()
    
    # METHOD 2: Try static HTML scraping (5-15 seconds)
    print("🌐 [2/4] STATIC HTML: Analyzing site structure...")
    try:
        static_urls = scrape_static_html_urls(start_url)
        if len(static_urls) >= 10:  # Good amount found
            print(f"🌐 SUCCESS! Static HTML found {len(static_urls)} URLs in ~10 seconds")
            all_urls.update(static_urls)
            if len(all_urls) >= 15:  # Combined with sitemap gives good coverage
                print("✅ Static + Sitemap methods sufficient - skipping heavy methods")
                save_urls_to_file(all_urls)
                return all_urls
        elif len(static_urls) >= 2:
            print(f"⚠️ Static HTML found {len(static_urls)} URLs (continuing to other methods)")
            all_urls.update(static_urls)
        else:
            print("📭 Static HTML scraping found minimal results")
    except Exception as e:
        print(f"❌ Static HTML scraping failed: {str(e)[:100]}...")
    
    # METHOD 3: Try Firecrawl API (30-60 seconds)
    print("🔥 [3/4] FIRECRAWL API: Cloud-based scraping...")
    try:
        api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
        if api_key:
            app: firecrawl.FirecrawlApp = firecrawl.FirecrawlApp(api_key=api_key)
            firecrawl_urls = crawl_all_pages(app, start_url)
            if len(firecrawl_urls) >= 5:
                print(f"🔥 SUCCESS! Firecrawl found {len(firecrawl_urls)} URLs")
                all_urls.update(firecrawl_urls)
                if len(all_urls) >= 20:  # Good total coverage
                    print("✅ Combined methods found sufficient URLs - skipping Playwright")
                    save_urls_to_file(all_urls)
                    return all_urls
            else:
                print(f"⚠️ Firecrawl found {len(firecrawl_urls)} URLs")
                all_urls.update(firecrawl_urls)
        else:
            print("❌ No Firecrawl API key found")
    except Exception as e:
        print(f"❌ Firecrawl API failed: {str(e)[:100]}...")
    
    # METHOD 4: Try Playwright browser automation (60+ seconds)
    if PLAYWRIGHT_AVAILABLE:
        print("🎭 [4/4] PLAYWRIGHT: Full browser automation (last resort)...")
        try:
            limits = get_crawl_limits()
            playwright_urls = crawl_with_playwright(
                start_url=start_url,
                limits=limits,
                delay=1.5,
                verbose=True
            )
            
            if len(playwright_urls) > 0:
                print(f"🎭 SUCCESS! Playwright found {len(playwright_urls)} URLs")
                all_urls.update(playwright_urls)
            else:
                print("🎭 Playwright found no additional URLs")
                
        except Exception as e:
            print(f"❌ Playwright failed: {str(e)[:100]}...")
    else:
        print("🎭 Playwright not available, skipping...")
    
    # FINAL: Return all URLs found by any method
    if len(all_urls) > 0:
        print(f"🏁 HYBRID COMPLETE: Found {len(all_urls)} total URLs across all methods")
        save_urls_to_file(all_urls)
        return all_urls
    else:
        print("❌ HYBRID FAILED: No URLs found by any method")
        return set()


def save_urls_to_file(urls: Set[str], filename: str = "data/main.txt") -> None:
    """
    Save a set of URLs to a text file with final validation and canonicalization.
    
    Args:
        urls (Set[str]): Set of URLs to save
        filename (str): Name of the output file (default: "data/main.txt")
    """
    # Final validation and canonicalization
    from pdp_filters import is_candidate_product_url, canonicalize_url
    
    clean_urls = set()
    rejected_count = 0
    
    for url in urls:
        try:
            base_netloc = urlparse(url).netloc
            if is_candidate_product_url(url, base_netloc):
                clean_url = canonicalize_url(url)
                clean_urls.add(clean_url)
            else:
                rejected_count += 1
        except:
            rejected_count += 1
            continue
    
    if rejected_count > 0:
        print(f"    Filtered out {rejected_count} non-product URLs")
    
    # Save to file
    with open(filename, 'a') as f:
        if f.tell() > 0:  # file isn't empty
            f.write('\n')
        for url in sorted(clean_urls):
            f.write(url + '\n')

    
    print(f"\nSaved {len(clean_urls)} validated product URLs to {filename}")


def main(start_url) -> None:
    """
    Main function to orchestrate the product page scraping process.
    """
    print("=== STRICT Product Page Scraper ===")
    print("This tool ONLY captures individual product pages where users can buy/add to cart.")
    print("It excludes: category pages, search results, media files, and listing pages.\n")
    
    # Get website URL from user
    if start_url is None:
        start_url: str = input("Enter the website URL to scrape: ").strip()
    
    # Ask about debug mode
    #debug_input = input("Enable debug mode for detailed validation info? (y/N): ").strip().lower()
    debug_mode = False
    
    if debug_mode:
        VALIDATION_CONFIG["debug_mode"] = True
        print("\nDebug mode enabled. You'll see detailed validation reasoning.\n")
    
    # Validate and normalize URL
    parsed = urlparse(start_url)
    if not parsed.scheme:
        # Add https:// if no scheme is provided
        start_url = 'https://' + start_url
    
    # Test if the site redirects to www or non-www and use the correct version
    try:
        app_test = firecrawl.FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY", ""))
        test_result = app_test.scrape(start_url, formats=['markdown'])
        if test_result and test_result.markdown:
            # Check if content contains www version of the domain
            if 'www.' + urlparse(start_url).netloc in test_result.markdown:
                # Site uses www version
                if not urlparse(start_url).netloc.startswith('www.'):
                    start_url = start_url.replace('://', '://www.', 1)
                    print(f"Detected site uses www version: {start_url}")
    except:
        pass  # Continue with original URL if test fails
    
    # Perform the scraping
    product_urls: Set[str] = scrape_product_pages(start_url)
    
    # Save results if any product pages were found
    if product_urls:
        save_urls_to_file(product_urls)
        print(f"\n[SUCCESS] Successfully found {len(product_urls)} product pages")
    else:
        print("\nNo product pages found.")
        print("\nPossible reasons:")
        print("- The site may use JavaScript rendering (not supported)")
        print("- No pages matched our strict product page criteria")
        print("- The site structure doesn't use standard e-commerce patterns")
        print("\nTry enabling debug mode to see validation details.")


if __name__ == "__main__":
    with open("main_pages.txt", "r") as file:
        for line in file:
            main(line.strip())
            with open("product_pages.txt", "a+") as f:
                f.seek(0, 2)  # move to end of file
                if f.tell() > 0:  # file has content
                    f.seek(f.tell() - 1)  # move to last character
                    last_char = f.read(1)
                    if last_char != "\n":
                        f.write("\n")  # add missing newline
# pdp_filters.py
import re, json
from urllib.parse import urlparse, urljoin, parse_qs, urlunparse

# -------- Same-origin + canonicalization --------
THIRD_PARTY_DENY_HOSTS = {
    'twitter.com','x.com','t.co','facebook.com','m.facebook.com',
    'pinterest.com','www.pinterest.com','linkedin.com','instagram.com'
}
SUBDOMAIN_DENY_PREFIXES = {'cdn','static','assets'}

TRACKING_KEYS_PREFIX = ('utm_','_ga','_gid','fbclid','gclid','srsltid','spm')
TRACKING_KEYS_EXACT = {
    'pr_prod_strat','pr_rec_id','pr_rec_pid','pr_ref_pid','pr_seq',
    'clickpr','clicktrk','affid','ref','refid'
}

def same_origin_strict(href: str, base_netloc: str) -> bool:
    h = urlparse(href).netloc.lower().lstrip('www.')
    b = base_netloc.lower().lstrip('www.')
    return h == b

def canonicalize_url(url: str) -> str:
    try:
        p = urlparse(url)
        params = parse_qs(p.query, keep_blank_values=True)
        clean = {}
        for k, v in params.items():
            kl = k.lower()
            if kl in TRACKING_KEYS_EXACT or any(kl.startswith(pref) for pref in TRACKING_KEYS_PREFIX):
                continue
            clean[k] = v
        q = '&'.join([f"{k}={''.join(v)}" for k,v in clean.items()])
        return urlunparse((p.scheme or 'https', p.netloc, p.path, '', q, ''))
    except:
        return url

# -------- Path rules (allow PDP, deny listings/utility) --------
PDP_ALLOW_PATTERNS = [
    r'^/products/[\w\-]+/?$',            # Shopify/BigCommerce
    r'^/product/[\w\-]+/?$',             # Woo/Magento-ish
    r'^/p/[\w\-]+/?$', r'^/dp/[\w\d]+/?$', r'^/item/[\w\-]+/?$',
    r'^/sku/[\w\-]+/?$', r'^/gp/product/[\w\-]+',
    r'^/catalog/product/view/',          # Magento
    r'^/product/\d+/?$',                 # Argos-like
    r'^/[\w\-]+\.html?$'                 # legacy html products
]

LISTING_DENY_PATTERNS = [
    r'/collections?/?$', r'/collections?/', r'/product-category/', r'/category/', r'/categories/',
    r'/catalog/', r'/search', r'[\?&]page=\d+', r'/page/\d+/?$',
    r'^/blog', r'^/news', r'^/article', r'^/post',
    r'^/help', r'^/support', r'^/faq', r'^/account', r'^/login', r'^/register',
    r'^/cart', r'^/basket', r'^/checkout', r'^/wishlist', r'^/compare',
    r'^/polic', r'^/privacy', r'^/terms', r'^/contact', r'^/pages/', r'^/apps/', r'^/cdn/',
]

def looks_like_pdp_path(path: str) -> bool:
    if any(re.search(p, path) for p in LISTING_DENY_PATTERNS):
        return False
    return any(re.search(p, path) for p in PDP_ALLOW_PATTERNS)

# -------- Final URL gate --------
def is_candidate_product_url(url: str, base_netloc: str) -> bool:
    p = urlparse(url)
    host_core = p.netloc.lower().lstrip('www.')
    base_core = base_netloc.lower().lstrip('www.')

    # third-party sharers/CDNs (hard deny)
    if host_core in THIRD_PARTY_DENY_HOSTS:
        return False
    if host_core.endswith(base_core):
        sub = host_core.replace(base_core, '').strip('.')
        if sub and sub.split('.')[0] in SUBDOMAIN_DENY_PREFIXES:
            return False

    # must be strict same-origin
    if not same_origin_strict(url, base_netloc):
        return False

    # path must look like PDP
    return looks_like_pdp_path(p.path)

# -------- Page-level validation (optional but powerful) --------
def has_product_jsonld(html: str) -> bool:
    # quick scan for @type":"Product" or "@type":["Product", ...]
    # (string search is faster than full JSON parse; cheap and good enough)
    t = html.lower()
    if '"@type"' not in t: return False
    return ('"product"' in t) or ("'product'" in t)

BUY_PAT = re.compile(r'(add\s*to\s*(cart|bag|basket)|buy\s*now|purchase\s*now|order\s*now)', re.I)
PRICE_PAT = re.compile(r'([$£€]\s*\d[\d,]*\.?\d*)', re.I)

def page_looks_like_pdp(html: str) -> bool:
    t = html
    if has_product_jsonld(t):
        return True
    # fallback: buy + price on same page
    return bool(BUY_PAT.search(t) and PRICE_PAT.search(t))

# -------- Playwright-scoped extraction (product grids only) --------
PRODUCT_LINK_SELECTORS = [
    # Shopify/BigCommerce
    'main a[href^="/products/"]',
    '.product-grid a[href*="/products/"]',
    '.card a[href*="/products/"]',
    # WooCommerce
    'ul.products li.product a.woocommerce-LoopProduct-link',
    # Magento-ish / generic
    'a.product-item-link',
    '[data-product-id] a[href]',
    '.product-card a[href], .product-tile a[href]',
    # generic fallback
    'a[href*="/product/"]',
]

def scoped_product_links_from_page(page, base_url: str) -> set:
    base_netloc = urlparse(base_url).netloc
    urls = set()
    for sel in PRODUCT_LINK_SELECTORS:
        for el in page.locator(sel).all():
            href = el.get_attribute('href') or ''
            if href.startswith('/'):
                href = urljoin(base_url, href)
            if href.startswith('http') and is_candidate_product_url(href, base_netloc):
                urls.add(canonicalize_url(href))
    return urls

# -------- Sitemaps (fast path) --------
import requests
from xml.etree import ElementTree as ET

def sitemap_pdp_urls(root_url: str, timeout=20) -> set:
    """Try /sitemap.xml, follow product sitemaps, return only PDP-looking URLs."""
    urls = set()
    base = urlparse(root_url)
    base_root = f"{base.scheme or 'https'}://{base.netloc}"
    try:
        r = requests.get(urljoin(base_root, '/sitemap.xml'), timeout=timeout)
        r.raise_for_status()
        xml = ET.fromstring(r.text)
        locs = [e.text for e in xml.iter() if e.tag.endswith('loc') and e.text]
        # recurse into product sitemaps first
        likely_product_sitemaps = [u for u in locs if any(x in u.lower() for x in ('product', 'products'))]
        targets = likely_product_sitemaps or locs
        for sm in targets[:20]:
            try:
                rs = requests.get(sm, timeout=timeout)
                rs.raise_for_status()
                sx = ET.fromstring(rs.text)
                for loc in sx.iter():
                    if not loc.tag.endswith('loc') or not loc.text: continue
                    u = loc.text.strip()
                    if is_candidate_product_url(u, base.netloc):
                        urls.add(canonicalize_url(u))
            except: 
                continue
    except:
        pass
    return urls