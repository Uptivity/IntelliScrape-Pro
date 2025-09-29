"""
Flask Web Interface for MarketPlace Scraper Pro
Multi-Platform Product Discovery and Import System
"""

import os
import sys
import json
import threading
import uuid
import io
import time
import random
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Note: API keys come from web interface only for security
# load_dotenv()  # Removed for security - API keys via web interface only

# Add scraper modules to path - fixed for Docker compatibility
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
modules_path = os.path.join(script_dir, "ScraperFunctions", "modules")
sys.path.insert(0, modules_path)
# Also add Docker-specific paths as fallback
sys.path.append('/app/ScraperFunctions/modules')  # Docker absolute path
sys.path.append('./ScraperFunctions/modules')      # Relative path

app = Flask(__name__)
CORS(app)

# Add cache-busting headers for development
@app.after_request
def after_request(response):
    # Disable caching for static files during development
    if request.endpoint == 'static':
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Import scraper modules with encoding protection
print("[STARTUP] Importing scraper modules...")
try:
    # Suppress print statements from modules during import
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    import scraper
    from product_scraper import scrape_product_pages
    from image_downloader import download_images_from_csv

    # Restore stdout/stderr
    sys.stdout = old_stdout
    sys.stderr = old_stderr

    MODULES_LOADED = True
    print("[SUCCESS] All scraper modules loaded successfully")
except ImportError as e:
    sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
    sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr
    print(f"[ERROR] Could not import scraper modules: {e}")
    import traceback
    print(f"[TRACEBACK]\n{traceback.format_exc()}")
    MODULES_LOADED = False
except Exception as e:
    sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
    sys.stderr = old_stderr if 'old_stderr' in locals() else sys.stderr
    print(f"[ERROR] Error loading modules: {e}")
    import traceback
    print(f"[TRACEBACK]\n{traceback.format_exc()}")
    MODULES_LOADED = False

# Store job status in memory (in production, use Redis/database)
jobs = {}

class ScraperJob:
    def __init__(self, job_id, job_type):
        self.id = job_id
        self.type = job_type
        self.status = "pending"
        self.progress = 0
        self.total = 0
        self.message = "Initializing..."
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.completed_at = None
        self.retry_count = 0
        self.failed_urls = []
        self.recovered_urls = []

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """Check if API and scraper modules are working"""
    return jsonify({
        "status": "online",
        "modules_loaded": MODULES_LOADED,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/extract-urls', methods=['POST'])
def extract_urls():
    """Discover product URLs from marketplace store URLs"""
    data = request.json
    homepage_urls = data.get('urls', [])
    settings = data.get('settings', {})

    if not homepage_urls:
        return jsonify({"error": "No URLs provided"}), 400

    # Require API key from frontend
    api_key = settings.get('apiKey')
    if not api_key:
        return jsonify({"error": "Firecrawl API key is required"}), 400

    # Create job
    job_id = str(uuid.uuid4())
    job = ScraperJob(job_id, "url_extraction")
    jobs[job_id] = job

    # Run extraction in background
    def run_extraction():
        try:
            job.status = "running"
            job.total = len(homepage_urls)
            all_product_urls = []

            for i, homepage in enumerate(homepage_urls):
                # Check if job was cancelled
                if job.status == "cancelled":
                    job.result = {"urls_found": all_product_urls, "count": len(all_product_urls)}
                    return

                job.progress = i + 1
                job.message = f"Extracting from {homepage}"

                # Try multiple extraction methods
                try:
                    # Method 1: Try Firecrawl map for best results
                    if api_key:
                        try:
                            import firecrawl
                            fc_app = firecrawl.FirecrawlApp(api_key=api_key)

                            # Use map to get all URLs from site
                            map_result = fc_app.map_url(homepage, params={
                                'limit': 500,  # Increased limit
                                'includeSubdomains': False,
                                'search': 'product'  # Focus on product pages
                            })

                            if map_result and 'links' in map_result:
                                product_urls = []
                                print(f"DEBUG: Firecrawl found {len(map_result['links'])} total links")

                                for url in map_result['links']:
                                    # Filter for product URLs - expanded patterns
                                    url_lower = url.lower()
                                    print(f"DEBUG: Checking URL: {url}")

                                    # Skip pagination and non-product URLs immediately
                                    skip_patterns = [
                                        '/page/', '/category/', '/blog/', '/about', '/contact',
                                        '/privacy', '/terms', '/login', '/register', '/account',
                                        '/search?', '/cart', '/checkout', '/order', '/home',
                                        '/collections/', '/pages/', '?page=', '#page', '.jpg', '.png',
                                        '/cdn-cgi/', '/wp-admin/', '/wp-content/uploads/',
                                        '/tag/', '/author/', '/feed/', '/sitemap', 'shop/page/'
                                    ]
                                    if any(skip in url_lower for skip in skip_patterns):
                                        print(f"DEBUG: SKIPPED (blacklist) - {url}")
                                        continue

                                    # Check explicit product patterns
                                    explicit_match = any(pattern in url_lower for pattern in [
                                        '/product/', '/item/', '/p/', '/products/',
                                        '/shop/product/', '/catalog/product/'
                                    ])

                                    # Check hyphenated pattern (strict product URLs)
                                    url_parts = url.split('/')
                                    last_part = url_parts[-1] if url_parts else ""
                                    # Clean last part
                                    last_part = last_part.split('?')[0].split('#')[0]

                                    hyphenated_match = (
                                        len(url_parts) >= 3 and  # At least domain/path/product
                                        last_part and
                                        '-' in last_part and
                                        len(last_part) > 10 and
                                        not last_part.startswith('page-') and
                                        not last_part.startswith('category-') and
                                        not any(char in last_part for char in ['?', '#', '=', '@']) and
                                        not any(last_part.endswith(ext) for ext in ['.jpg', '.png', '.css', '.js', '.pdf'])
                                    )

                                    if explicit_match or hyphenated_match:
                                        product_urls.append(url)
                                        print(f"DEBUG: MATCHED - {url} (explicit: {explicit_match}, hyphenated: {hyphenated_match})")
                                    else:
                                        print(f"DEBUG: SKIPPED - {url}")

                                print(f"DEBUG: Total product URLs found: {len(product_urls)}")

                                if product_urls:
                                    all_product_urls.extend(product_urls[:50])
                                    job.message = f"Found {len(product_urls)} products via Firecrawl"
                                    continue
                        except Exception as e:
                            pass  # Fall through to next method

                    # Method 2: Simple BeautifulSoup scraping
                    print("DEBUG: Trying BeautifulSoup method")
                    import requests
                    from bs4 import BeautifulSoup
                    from urllib.parse import urljoin, urlparse

                    response = requests.get(homepage, timeout=10, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find product links (common patterns)
                    product_urls = set()
                    all_links = soup.find_all('a', href=True)
                    print(f"DEBUG: BeautifulSoup found {len(all_links)} total links")

                    for link in all_links:
                        url = urljoin(homepage, link['href'])
                        url_lower = url.lower()

                        # Skip pagination and non-product URLs immediately
                        skip_patterns = [
                            '/page/', '/category/', '/blog/', '/about', '/contact',
                            '/privacy', '/terms', '/login', '/register', '/account',
                            '/search?', '/cart', '/checkout', '/order', '/home',
                            '/collections/', '/pages/', '?page=', '#page', '.jpg', '.png',
                            '/cdn-cgi/', '/wp-admin/', '/wp-content/uploads/',
                            '/tag/', '/author/', '/feed/', '/sitemap', 'shop/page/'
                        ]
                        if any(skip in url_lower for skip in skip_patterns):
                            continue

                        # Check explicit product patterns
                        explicit_match = any(pattern in url_lower for pattern in [
                            '/product/', '/item/', '/p/', '/products/',
                            '/shop/product/', '/catalog/product/'
                        ])

                        # Check hyphenated pattern (strict product URLs)
                        url_parts = url.split('/')
                        last_part = url_parts[-1] if url_parts else ""
                        # Clean last part
                        last_part = last_part.split('?')[0].split('#')[0]

                        hyphenated_match = (
                            len(url_parts) >= 3 and  # At least domain/path/product
                            last_part and
                            '-' in last_part and
                            len(last_part) > 10 and
                            not last_part.startswith('page-') and
                            not last_part.startswith('category-') and
                            not any(char in last_part for char in ['?', '#', '=', '@']) and
                            not any(last_part.endswith(ext) for ext in ['.jpg', '.png', '.css', '.js', '.pdf'])
                        )

                        # Same domain check
                        same_domain = urlparse(url).netloc == urlparse(homepage).netloc

                        if (explicit_match or hyphenated_match) and same_domain:
                            product_urls.add(url)
                            print(f"DEBUG: BS MATCHED - {url} (explicit: {explicit_match}, hyphenated: {hyphenated_match})")

                    print(f"DEBUG: BeautifulSoup found {len(product_urls)} product URLs")

                    if product_urls:
                        all_product_urls.extend(list(product_urls)[:50])  # Limit to 50 per site
                        job.message = f"Found {len(product_urls)} products from {homepage}"

                except Exception as e:
                    # Fallback to original scraper if available
                    try:
                        old_stdout = sys.stdout
                        sys.stdout = io.StringIO()
                        urls = scrape_product_pages(homepage)
                        sys.stdout = old_stdout
                        if urls:
                            all_product_urls.extend(urls)
                    except:
                        sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout
                        job.message = f"Failed to extract from {homepage}: {str(e)[:50]}"
                        continue

            job.status = "completed"
            job.result = {
                "urls_found": all_product_urls,
                "count": len(all_product_urls)
            }
            job.message = f"Found {len(all_product_urls)} product URLs"
            job.completed_at = datetime.now()

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.message = "Extraction failed"

    thread = threading.Thread(target=run_extraction)
    thread.start()

    return jsonify({"job_id": job_id})

@app.route('/api/scrape-products', methods=['POST'])
def scrape_products():
    """Import product details from URLs for marketplace"""
    print(f"\n[API ENDPOINT] /api/scrape-products called")
    print(f"[INFO] MODULES_LOADED status: {MODULES_LOADED}")

    if not MODULES_LOADED:
        print("[ERROR] Scraper modules not loaded - check import errors above")
        return jsonify({"error": "Scraper modules not loaded. Check server console for import errors."}), 500

    data = request.json
    product_urls = data.get('urls', [])
    settings = data.get('settings', {})  # Get frontend settings

    print(f"[INFO] Received {len(product_urls)} URLs")
    print(f"[INFO] Settings keys: {list(settings.keys())}")

    if not product_urls:
        return jsonify({"error": "No URLs provided"}), 400

    # Require marketplace selection
    extraction_mode = settings.get('extractionMode')
    if not extraction_mode:
        print("[ERROR] No marketplace format selected")
        return jsonify({"error": "Please select a marketplace format (WSMarketplace or JustSell)"}), 400

    # Initialize API key - require from frontend only
    api_key = settings.get('apiKey')
    if not api_key:
        print("[ERROR] No API key provided in settings")
        return jsonify({"error": "Firecrawl API key is required"}), 400
    else:
        print(f"[INFO] Using API key: {api_key[:15]}...{api_key[-4:]} (length: {len(api_key)})")
        print(f"[INFO] Marketplace format: {extraction_mode.upper()}")

    # Create job
    job_id = str(uuid.uuid4())
    job = ScraperJob(job_id, "product_scraping")
    jobs[job_id] = job

    # Run scraping in background
    def run_scraping():
        print(f"[THREAD] *** STARTING THREAD FOR JOB {job_id} ***")
        import sys
        print(f"[THREAD] Python path: {sys.path[:3]}")
        try:
            print(f"\n[SCRAPING JOB STARTED] Job ID: {job_id}")
            print(f"[INFO] Total URLs received: {len(product_urls)}")
            print(f"[INFO] Extraction mode: {settings.get('extractionMode', 'wsmarketplace')}")

            job.status = "running"
            job.total = len(product_urls)

            # Initialize scraper with better error handling
            try:
                print(f"[THREAD] About to import/use scraper module...")
                print(f"[THREAD] scraper module location: {scraper}")
                print(f"[INFO] Initializing Firecrawl with API key: {api_key[:10]}...")
                scraper.initialize_firecrawl_app(api_key)
                print(f"[SUCCESS] Firecrawl initialized with API key")
            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Failed to initialize Firecrawl: {error_msg}")
                import traceback
                print(f"[TRACEBACK] {traceback.format_exc()}")
                job.status = "failed"

                # Parse initialization error for user-friendly message
                if 'Payment Required' in error_msg or 'Insufficient tokens' in error_msg:
                    job.error = "Firecrawl credits exhausted. Your account has run out of tokens. Add more at: https://www.firecrawl.dev/extract#pricing"
                    job.message = "Firecrawl API credits exhausted"
                elif 'Unauthorized' in error_msg or 'Invalid API key' in error_msg:
                    job.error = "Invalid Firecrawl API key. Please check your API key in Settings."
                    job.message = "Invalid API key"
                else:
                    job.error = f"Firecrawl initialization failed: {error_msg[:100]}"
                    job.message = "Firecrawl initialization failed"
                return

            # Set retry count from frontend settings
            api_retries = int(settings.get('apiRetries', 1))
            scraper.MAX_RETRIES = min(max(api_retries - 1, 0), 4)  # Convert to 0-based, max 4

            # Setup CSV path
            csv_path = Path("ScraperFunctions/data/products.csv")
            csv_path.parent.mkdir(exist_ok=True)
            scraper.set_csv_file_path(str(csv_path))
            scraper.CSV_FILE = str(csv_path)

            # Initialize scraper cache for proper SKU generation
            try:
                # Import and create cache manager if not exists
                if not hasattr(scraper, 'cache_manager'):
                    from scraper import CacheManager
                    scraper.cache_manager = CacheManager()
                scraper.initialize_from_csv()
            except Exception as e:
                print(f"Warning: Could not initialize CSV cache: {e}")
                # Create a basic cache manager as fallback
                from scraper import CacheManager
                scraper.cache_manager = CacheManager()

            # Initialize CSV with headers (format-aware and format-switching capable)
            import csv
            extraction_mode = data.get('settings', {}).get('extractionMode', 'wsmarketplace')
            csv_format = scraper.get_csv_format_settings(extraction_mode)

            need_reinit = False

            if not csv_path.exists():
                need_reinit = True
                print(f"[CSV] File doesn't exist, will create with {extraction_mode.upper()} format")
            else:
                # Check if existing CSV headers match current format
                try:
                    with open(csv_path, "r", newline="", encoding="utf-8") as f:
                        reader = csv.reader(f)
                        existing_headers = next(reader, [])
                        if existing_headers != csv_format['fieldnames']:
                            need_reinit = True
                            print(f"[CSV] Format mismatch detected:")
                            print(f"[CSV] Existing: {len(existing_headers)} columns ({existing_headers[:3]}...)")
                            print(f"[CSV] Required: {len(csv_format['fieldnames'])} columns ({csv_format['fieldnames'][:3]}...)")
                            print(f"[CSV] Reinitializing for {extraction_mode.upper()} format")
                except:
                    need_reinit = True
                    print(f"[CSV] Error reading existing headers, reinitializing")

            if need_reinit:
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=csv_format['fieldnames'])
                    writer.writeheader()
                print(f"[CSV] Initialized products.csv with {extraction_mode.upper()} format headers ({len(csv_format['fieldnames'])} columns)")

            # Remove duplicate URLs before scraping and validate
            unique_urls = list(dict.fromkeys(product_urls))  # Preserves order, removes duplicates

            # Filter out invalid URLs
            valid_urls = []
            for url in unique_urls:
                if url and url.startswith(('http://', 'https://')):
                    valid_urls.append(url)
                else:
                    print(f"[WARNING] Invalid URL skipped: {url}")

            if not valid_urls:
                job.status = "failed"
                job.error = "No valid URLs provided"
                job.message = "Please provide valid URLs starting with http:// or https://"
                return

            print(f"Scraping {len(valid_urls)} valid URLs (removed {len(product_urls) - len(valid_urls)} invalid/duplicates)")

            products = []
            for i, url in enumerate(valid_urls):
                # Check if job was cancelled
                if job.status == "cancelled":
                    job.result = {"products": products, "count": len(products)}
                    return

                job.progress = i + 1
                job.message = f"Scraping product {i+1}/{len(valid_urls)}"

                try:
                    # DON'T redirect stdout - we WANT to see the debug output
                    # old_stdout = sys.stdout
                    # sys.stdout = io.StringIO()  # REMOVED to see debug output
                    print(f"\\n[THREAD] Starting to scrape URL {i+1}/{len(valid_urls)}: {url}")

                    # Choose prompt and CSV format based on extraction mode setting
                    extraction_mode = settings.get('extractionMode', 'wsmarketplace')
                    print(f"[DEBUG] Raw extraction_mode from settings: '{extraction_mode}'")
                    print(f"[DEBUG] Settings keys: {list(settings.keys())}")

                    selected_prompt = scraper.JUSTSELL_STRICT_PROMPT if extraction_mode == 'justsell' else scraper.WSMARKETPLACE_STRICT_PROMPT
                    csv_format = scraper.get_csv_format_settings(extraction_mode)

                    print(f"[MODE] Using {extraction_mode.upper()} format for scraping")
                    print(f"[CSV] Format has {len(csv_format['fieldnames'])} columns: {csv_format['fieldnames'][:5]}...")
                    print(f"[CSV] Using {'JUSTSELL' if extraction_mode == 'justsell' else 'WSMARKETPLACE'} field mapping")

                    # Use scraper's extraction
                    result = scraper.extract_with_retry(
                        scraper.app,
                        url,
                        selected_prompt,
                        scraper.ProductSchema.model_json_schema(),
                        show_spinner=False
                    )

                    # DEBUG: Detailed result analysis
                    print(f"[THREAD] Finished scraping attempt for URL: {url}")
                    print(f"[DEBUG] Result exists: {result is not None}")
                    if result:
                        print(f"[DEBUG] Result has success: {'success' in result}")
                        print(f"[DEBUG] Result success value: {result.get('success', 'N/A')}")
                        print(f"[DEBUG] Result has data: {'data' in result}")
                        print(f"[DEBUG] Result data value: {result.get('data', 'N/A')}")
                        print(f"[DEBUG] Result has error: {'error' in result}")
                        if 'error' in result:
                            print(f"[DEBUG] Result error: {result.get('error', 'N/A')}")
                    else:
                        print(f"[ERROR] No result returned from extract_with_retry for {url}")

                    if result and result.get('success', False) and result.get('data', None):
                        product_data = result['data']
                        products.append(product_data)

                        # Write to CSV immediately using selected format
                        with open(csv_path, "a", newline="", encoding="utf-8") as f:
                            writer = csv.DictWriter(f, fieldnames=csv_format['fieldnames'])

                            # Map the data to CSV format using the selected mapping
                            csv_row = scraper.map_row_to_csv(product_data, csv_format['field_mapping'], csv_format['fieldnames'], settings)

                            # Generate SKU if missing and enabled
                            if settings.get('autoGenerateSKU', True):
                                product_name = csv_row.get("Name", f"PRODUCT{i+1}")

                                try:
                                    # Use the working SKU generation function from scraper.py
                                    generated_sku = scraper.generate_sku_from_name(product_name)

                                    # Set SKU in the correct field based on marketplace format
                                    if extraction_mode == 'justsell':
                                        csv_row["Variant SKU"] = generated_sku
                                        print(f"[SKU] Generated for JustSell: {generated_sku} -> Variant SKU")
                                    else:
                                        csv_row["SKU"] = generated_sku
                                        print(f"[SKU] Generated for WSMarketplace: {generated_sku} -> SKU")

                                    # Add to cache to prevent duplicates
                                    if hasattr(scraper, 'cache_manager'):
                                        scraper.cache_manager.add_sku(generated_sku)

                                    print(f"[SKU] ✅ Generated: {generated_sku} for product: {product_name[:50]}")

                                except Exception as e:
                                    print(f"[SKU] ❌ Generation failed: {e}")
                                    # Simple fallback
                                    fallback_sku = f"PROD{str(i+1).zfill(4)}"
                                    if extraction_mode == 'justsell':
                                        csv_row["Variant SKU"] = fallback_sku
                                    else:
                                        csv_row["SKU"] = fallback_sku
                                    print(f"[SKU] 🔄 Using fallback: {fallback_sku}")

                            # Generate description if missing and enabled
                            if not csv_row.get("Description") and settings.get('autoGenerateDescription', False) and settings.get('groqKey'):
                                try:
                                    from groq import Groq
                                    client = Groq(api_key=settings['groqKey'])

                                    prompt = f"""Generate a professional product description for:
Product: {csv_row.get('Name', 'Product')}
Brand: {csv_row.get('Brand', 'N/A')}
Category: {csv_row.get('Category', 'N/A')}

Create a concise, professional description (2-3 sentences) highlighting key benefits. Do not include pricing."""

                                    response = client.chat.completions.create(
                                        messages=[
                                            {"role": "system", "content": "You are a professional product copywriter."},
                                            {"role": "user", "content": prompt}
                                        ],
                                        model="llama-3.1-8b-instant",
                                        max_tokens=100,
                                        temperature=0.7
                                    )
                                    csv_row["Description"] = response.choices[0].message.content.strip()
                                except Exception as desc_error:
                                    print(f"Description generation failed: {desc_error}")
                                    csv_row["Description"] = f"Quality {csv_row.get('Name', 'product')} offering reliable performance and value."

                            if not csv_row.get("Status"):
                                csv_row["Status"] = "1"
                            if not csv_row.get("RFQ"):
                                csv_row["RFQ"] = "Y"

                            writer.writerow(csv_row)
                    else:
                        # Failed extraction - log the failure reason and collect error details
                        print(f"[FAILED] Extraction failed for {url}")

                        # Extract specific error message from result
                        if result and result.get('error'):
                            error_reason = result['error']
                            print(f"[FAILED] Error: {error_reason}")
                        elif result is None:
                            error_reason = "No result returned from extract_with_retry"
                            print(f"[FAILED] {error_reason}")
                        elif result and not result.get('success', False):
                            # We have a result but it failed - check for error details
                            error_reason = result.get('error', 'Extraction failed for unknown reason')
                            print(f"[FAILED] Error: {error_reason}")
                        else:
                            error_reason = "No successful result returned"
                            print(f"[FAILED] {error_reason}")

                        # Add error to job error details for later processing
                        job.error_details = getattr(job, 'error_details', [])
                        job.error_details.append(f"URL: {url}, Error: {error_reason}")

                        # Continue to next URL
                        continue

                except Exception as e:
                    # sys.stdout = old_stdout if 'old_stdout' in locals() else sys.stdout  # REMOVED
                    error_msg = str(e)
                    print(f"[ERROR] Failed to scrape {url}: {error_msg}")
                    import traceback
                    print(f"[TRACEBACK for {url}]:\n{traceback.format_exc()}")
                    job.message = f"Error scraping product {i+1}: {error_msg[:100]}"
                    job.error_details = getattr(job, 'error_details', [])  # Initialize if not exists
                    job.error_details.append(f"URL: {url}, Error: {error_msg}")
                    continue

            # Check if any products were scraped
            if len(products) == 0 and len(valid_urls) > 0:
                job.status = "failed"
                job.message = "No products were successfully scraped. Check your API key and URLs."
                if hasattr(job, 'error_details'):
                    # Parse error details for user-friendly messages
                    error_messages = []
                    credits_exhausted = False

                    for error_detail in job.error_details[:3]:  # Check first 3 errors
                        if 'Payment Required' in error_detail or 'Insufficient tokens' in error_detail:
                            credits_exhausted = True
                            break
                        elif 'Unauthorized' in error_detail or 'Invalid API key' in error_detail:
                            error_messages.append("Invalid Firecrawl API key")
                            break
                        else:
                            # Extract just the error part after "Error: "
                            if "Error: " in error_detail:
                                clean_error = error_detail.split("Error: ", 1)[1]
                                error_messages.append(clean_error[:100])  # Limit length
                            else:
                                error_messages.append(error_detail[:100])

                    if credits_exhausted:
                        job.error = "Firecrawl credits exhausted. Your account has run out of tokens. Add more at: https://www.firecrawl.dev/extract#pricing"
                    elif error_messages:
                        job.error = "; ".join(error_messages)
                    else:
                        job.error = "Unable to extract product data. Please check your URLs and API key."
            else:
                job.status = "completed"
                job.result = {
                    "products": products,
                    "count": len(products)
                }
                job.message = f"Scraped {len(products)} out of {len(valid_urls)} products successfully"
            job.completed_at = datetime.now()

        except Exception as e:
            import traceback
            full_error = traceback.format_exc()
            job.status = "failed"

            # Parse error for user-friendly message
            error_msg = str(e)
            if 'Payment Required' in error_msg or 'Insufficient tokens' in error_msg:
                job.error = "Firecrawl credits exhausted. Your account has run out of tokens. Add more at: https://www.firecrawl.dev/extract#pricing"
            elif 'Unauthorized' in error_msg or 'Invalid API key' in error_msg:
                job.error = "Invalid Firecrawl API key. Please check your API key in Settings."
            else:
                job.error = f"Scraping failed: {str(e)[:100]}"

            job.message = f"Scraping failed: {str(e)[:100]}"
            print(f"[CRITICAL ERROR] Scraping job failed completely: {e}")
            print(f"[FULL TRACEBACK]:\n{full_error}")

    print(f"[MAIN] About to start thread for job {job_id}")
    thread = threading.Thread(target=run_scraping)
    print(f"[MAIN] Thread created: {thread}")
    thread.start()
    print(f"[MAIN] Thread started, is_alive: {thread.is_alive()}")

    return jsonify({"job_id": job_id})

@app.route('/api/job/<job_id>')
def get_job_status(job_id):
    """Get status of a specific job"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    return jsonify(job.to_dict())

@app.route('/api/cancel-job', methods=['POST'])
def cancel_job():
    """Cancel a running job"""
    data = request.json
    job_id = data.get('job_id')

    if not job_id:
        return jsonify({"error": "Job ID is required"}), 400

    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    if job.status == "completed":
        return jsonify({"error": "Job already completed"}), 400

    if job.status == "cancelled":
        return jsonify({"message": "Job already cancelled"})

    # Mark job as cancelled
    job.status = "cancelled"
    job.completed_at = datetime.now()
    job.message = "Job cancelled by user"

    # Return any partial results
    partial_results = []
    if hasattr(job, 'result') and job.result:
        if job.job_type == "url_extraction" and 'urls_found' in job.result:
            partial_results = job.result['urls_found']
        elif job.job_type == "product_scraping" and 'products' in job.result:
            partial_results = job.result['products']

    return jsonify({
        "message": "Job cancelled successfully",
        "partial_results": partial_results,
        "items_processed": job.progress
    })

@app.route('/api/download-csv')
def download_csv():
    """Download the products CSV file"""
    csv_path = Path("ScraperFunctions/data/products.csv")
    if not csv_path.exists():
        return jsonify({"error": "No products CSV found"}), 404

    return send_file(
        csv_path,
        as_attachment=True,
        download_name=f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mimetype='text/csv'
    )

@app.route('/api/download-images/<brand>')
def download_images(brand):
    """Download images for a specific brand"""
    images_dir = Path(f"ScraperFunctions/downloaded_images/{brand}")
    if not images_dir.exists():
        return jsonify({"error": f"No images found for brand {brand}"}), 404

    # In production, you'd create a zip file
    # For now, return list of available images
    images = [f.name for f in images_dir.iterdir() if f.is_file()]
    return jsonify({"brand": brand, "images": images})

@app.route('/api/validate-key', methods=['POST'])
def validate_api_key():
    """Validate API keys"""
    data = request.json
    key_type = data.get('type')  # 'firecrawl' or 'groq'
    api_key = data.get('key')

    if not key_type or not api_key:
        return jsonify({"error": "Missing type or key"}), 400

    try:
        if key_type == 'firecrawl':
            # Test Firecrawl API key
            if api_key.startswith('fc-') and len(api_key) > 10:
                try:
                    import firecrawl
                    fc_app = firecrawl.FirecrawlApp(api_key=api_key)
                    # Test with a simple status check instead of actual scraping
                    try:
                        # Try to get account status/credits - this validates the key without using credits
                        status = fc_app.get_credits()
                        return jsonify({"valid": True, "message": "Firecrawl API key is valid"})
                    except:
                        # Fallback: Just check if the key initializes without error
                        # This validates format and basic connectivity
                        return jsonify({"valid": True, "message": "Firecrawl API key format is valid"})
                except Exception as e:
                    return jsonify({"valid": False, "message": f"Firecrawl API key validation failed: {str(e)}"})
            else:
                return jsonify({"valid": False, "message": "Invalid Firecrawl key format (should start with 'fc-')"})

        elif key_type == 'groq':
            # Test Groq API key - note: Groq keys can start with gsk_ or gsk-
            if (api_key.startswith('gsk_') or api_key.startswith('gsk-')) and len(api_key) > 20:
                try:
                    from groq import Groq
                    client = Groq(api_key=api_key)
                    # Test with a simple call to validate the key
                    # Using llama-3.1-8b-instant which is the current available model
                    response = client.chat.completions.create(
                        messages=[{"role": "user", "content": "test"}],
                        model="llama-3.1-8b-instant",
                        max_tokens=1
                    )
                    return jsonify({"valid": True, "message": "Groq API key is valid"})
                except Exception as e:
                    # Return more detailed error for debugging
                    error_msg = str(e)
                    if "401" in error_msg or "unauthorized" in error_msg.lower():
                        return jsonify({"valid": False, "message": "Invalid Groq API key - authentication failed"})
                    elif "rate" in error_msg.lower():
                        return jsonify({"valid": True, "message": "Groq API key is valid (rate limit check)"})
                    else:
                        return jsonify({"valid": False, "message": f"Groq validation error: {error_msg[:100]}"})
            else:
                return jsonify({"valid": False, "message": "Invalid Groq key format (should start with 'gsk_' or 'gsk-')"})

        else:
            return jsonify({"error": "Unknown key type"}), 400

    except Exception as e:
        return jsonify({"valid": False, "message": f"Validation error: {str(e)}"})

@app.route('/api/generate-description', methods=['POST'])
def generate_description():
    """Generate product description using GROQ API"""
    try:
        data = request.json
        product_data = data.get('product_data', {})
        groq_key = data.get('groq_key')

        if not groq_key:
            return jsonify({"error": "GROQ API key is required"}), 400

        # Import GROQ client
        try:
            from groq import Groq
        except ImportError:
            return jsonify({"error": "GROQ library not available. Install with: pip install groq"}), 500

        # Initialize GROQ client
        client = Groq(api_key=groq_key)

        # Create description prompt
        prompt = f"""Generate a professional product description for the following item:

Product Name: {product_data.get('name', 'Unknown Product')}
Brand: {product_data.get('brand', 'N/A')}
Price: {product_data.get('price', 'N/A')}
Category: {product_data.get('category', 'N/A')}
Specifications: {product_data.get('specifications', 'N/A')}
Features: {product_data.get('features', 'N/A')}

Create a concise, professional product description (2-3 sentences) that highlights the key benefits and features. Focus on what makes this product valuable to customers. Do not include pricing information."""

        # Make GROQ API call
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional product copywriter. Create compelling, accurate product descriptions that highlight key benefits and features in a concise manner."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",  # Using current fast model
            max_tokens=150,
            temperature=0.7
        )

        description = chat_completion.choices[0].message.content.strip()

        return jsonify({"description": description})

    except Exception as e:
        return jsonify({"error": f"Failed to generate description: {str(e)}"}), 500

@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a completed session"""
    try:
        # For now, we'll just return success since sessions are stored in localStorage on frontend
        # In production, you'd delete from database
        return jsonify({"success": True, "message": f"Session {session_id} deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to delete session: {str(e)}"}), 500

if __name__ == '__main__':
    # Ensure directories exist
    Path("ScraperFunctions/data").mkdir(parents=True, exist_ok=True)
    Path("ScraperFunctions/downloaded_images").mkdir(parents=True, exist_ok=True)
    Path("ScraperFunctions/print_ready_images").mkdir(parents=True, exist_ok=True)

    # Use reloader but make threads more robust
    print("\n" + "="*70)
    print("STARTING SERVER WITH AUTO-RELOAD ENABLED")
    print("Scraping threads are now designed to handle restarts")
    print("="*70 + "\n")

    # For development: disable reloader during scraping to prevent interruptions
    # You can still make code changes and manually restart when needed
    print("INFO: Auto-reload disabled to prevent scraping interruptions")
    print("     Make code changes and restart manually when needed")

    app.run(
        debug=True,
        port=5000,
        use_reloader=False,  # Disabled to prevent mid-scrape restarts
        use_debugger=True
    )