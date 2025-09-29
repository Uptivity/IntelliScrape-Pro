import csv
import os
import re
import requests
from urllib.parse import urlparse
import time
from pathlib import Path
from PIL import Image
import io
import json
import ast
from tqdm import tqdm

URL_REGEX = re.compile(r'https?://[^\s,<>"\'\]]+', re.IGNORECASE)

def convert_any_image_to_webp(image_data, output_path):
    """Convert any image format to WebP - handles transparency properly to avoid artifacts"""
    try:
        with Image.open(image_data) as img:
            # Handle transparency properly to avoid green/matrix artifacts
            if img.mode == 'P':
                # Check if palette has transparency
                if 'transparency' in img.info:
                    img = img.convert('RGBA')
                else:
                    img = img.convert('RGB')
            elif img.mode in ('RGBA', 'LA'):
                # Keep transparency but ensure it's clean
                if img.mode == 'LA':
                    img = img.convert('RGBA')
                # Keep as RGBA for WebP transparency support
            elif img.mode in ('1', 'L'):
                # Grayscale to RGB
                img = img.convert('RGB')
            else:
                # Everything else to RGB (handles weird modes)
                img = img.convert('RGB')
            
            # Save as WebP with proper settings for transparency
            if img.mode == 'RGBA':
                # Use lossless for transparency to avoid green artifacts
                img.save(output_path, 'WEBP', lossless=True, method=6)
            else:
                # Use lossy for non-transparent images (smaller files)
                img.save(output_path, 'WEBP', quality=85, method=6)
            return True
    except Exception:
        return False

def parse_image_urls(images_data: str) -> list[str]:
    """Parse the CSV 'images' cell into a list of URLs."""
    if not images_data or not images_data.strip():
        return []

    # Try parsing as JSON first
    try:
        parsed = json.loads(images_data.strip())
        if isinstance(parsed, list):
            return [clean_url(url) for url in parsed if isinstance(url, str) and url.strip()]
        elif isinstance(parsed, str):
            return [clean_url(parsed.strip())] if parsed.strip() else []
    except json.JSONDecodeError:
        pass

    # Try parsing as Python literal (e.g., ['url1', 'url2'])
    try:
        parsed = ast.literal_eval(images_data.strip())
        if isinstance(parsed, list):
            return [clean_url(url) for url in parsed if isinstance(url, str) and url.strip()]
        elif isinstance(parsed, str):
            return [clean_url(parsed.strip())] if parsed.strip() else []
    except (ValueError, SyntaxError):
        pass

    # Parse semicolon-separated URLs (scraper format)
    if ';' in images_data:
        urls = [url.strip() for url in images_data.split(';')]
        return [clean_url(url) for url in urls if url.strip()]

    # Fall back to regex extraction
    urls = URL_REGEX.findall(images_data)
    return [clean_url(url.strip()) for url in urls if url.strip()]

def clean_url(url: str) -> str:
    """Clean URL by removing trailing punctuation and invalid characters"""
    if not url:
        return url
    
    # Remove trailing punctuation and semicolons
    url = url.rstrip('.,;:!?)"\']}')
    
    # Remove any leading colons or semicolons
    url = url.lstrip(':;')
    
    # Ensure it's a valid URL format
    if url and not url.startswith(('http://', 'https://')):
        return ''
    
    return url

def download_images_from_csv(csv_file_path='products.csv',
                             download_folder='downloaded_images',
                             images_column='Images',
                             brand_column='Brand',
                             sku_column='SKU'):
    """
    Downloads product images with professional progress interface.
    """
    Path(download_folder).mkdir(parents=True, exist_ok=True)

    total_images = 0
    downloaded_count = 0
    skipped_count = 0
    failed_count = 0
    failed_urls = []

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (compatible; ImageDownloader/1.0)'
    })

    try:
        with open(csv_file_path, 'r', encoding='utf-8', newline='') as csvfile:
            sample = csvfile.read(2048)
            csvfile.seek(0)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
                delimiter = dialect.delimiter
            except Exception:
                delimiter = ','

            reader = csv.DictReader(csvfile, delimiter=delimiter)
            if images_column not in reader.fieldnames:
                raise ValueError(f"Column '{images_column}' not found in CSV. Columns: {reader.fieldnames}")

            print(f"Found '{images_column}' column. Starting image downloads...")
            
            # First pass: collect all data and count images
            rows_data = []
            for row_index, row in enumerate(reader, start=1):
                raw_cell = row.get(images_column, '') or ''
                image_urls = parse_image_urls(raw_cell)
                # Deduplicate
                seen = set()
                image_urls = [u for u in image_urls if not (u in seen or seen.add(u))]
                
                if image_urls:
                    rows_data.append({
                        'row_index': row_index,
                        'row': row,
                        'image_urls': image_urls
                    })
                    total_images += len(image_urls)
            
            if total_images == 0:
                print("No images found to download.")
                return {
                    'total_images': 0,
                    'downloaded': 0,
                    'skipped': 0,
                    'failed': 0
                }
            
            print(f"Found {total_images} images to process...")
            print()
            
            # Second pass: download with professional progress bar
            with tqdm(total=total_images, desc="Downloading images", unit="image", ncols=80) as pbar:
                for row_data in rows_data:
                    row_index = row_data['row_index']
                    row = row_data['row']
                    image_urls = row_data['image_urls']

                    brand_name = (row.get(brand_column) or 'Unknown_Brand').strip() or 'Unknown_Brand'
                    # Take only the first word of the brand name and capitalize
                    first_word = brand_name.split()[0] if brand_name.split() else brand_name
                    clean_brand = re.sub(r'[<>:"/\\|?*]', '_', first_word.upper())
                    brand_dir = Path(download_folder) / clean_brand
                    brand_dir.mkdir(parents=True, exist_ok=True)

                    sku = (row.get(sku_column) or '').strip()
                    sku_safe = re.sub(r'[<>:"/\\|?* ]', '_', sku) if sku else None
                    product_name = (row.get('Name') or 'Unknown Product').strip()

                    for url_index, image_url in enumerate(image_urls, start=1):
                        try:
                            parsed_url = urlparse(image_url)
                            if not parsed_url.scheme.startswith('http'):
                                raise ValueError("Unsupported URL scheme")

                            # Filename logic
                            if sku_safe:
                                base_name = f"{sku_safe}_{url_index}"
                            else:
                                orig_name = os.path.basename(parsed_url.path) or f"row{row_index}_{url_index}.jpg"
                                base_name, _ = os.path.splitext(orig_name)

                            filename = re.sub(r'[<>:"/\\|?*]', '_', f"{base_name}.webp")
                            file_path = brand_dir / filename

                            # Check if file already exists
                            if file_path.exists():
                                filename_display = file_path.name
                                tqdm.write(f"  ~ SKIP: {filename_display} ({product_name[:30]}{'...' if len(product_name) > 30 else ''}) - already exists")
                                skipped_count += 1
                                pbar.update(1)
                                continue

                            # Ensure uniqueness with counter
                            counter = 1
                            original_file_path = file_path
                            while file_path.exists():
                                file_path = brand_dir / f"{base_name}_{counter}.webp"
                                counter += 1

                            # Handle Google Drive/Photos URLs
                            download_url = image_url
                            if "drive.google.com" in image_url:
                                if "/file/d/" in image_url and "/view" in image_url:
                                    file_id = image_url.split("/file/d/")[1].split("/")[0]
                                    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                            elif "photos.google.com" in image_url or "googleusercontent.com" in image_url:
                                if "=" not in image_url:
                                    download_url = f"{image_url}=s2048"

                            # Download with headers
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Referer': 'https://www.google.com/'
                            }
                            
                            with session.get(download_url, headers=headers, timeout=30, stream=True) as resp:
                                resp.raise_for_status()
                                
                                # Check content type
                                content_type = resp.headers.get('Content-Type', '').lower()
                                if 'text/html' in content_type:
                                    raise ValueError(f"Got HTML instead of image: {content_type}")
                                
                                image_data = io.BytesIO()
                                for chunk in resp.iter_content(chunk_size=8192):
                                    if chunk:
                                        image_data.write(chunk)
                                image_data.seek(0)
                                
                                # Verify it's image data
                                first_bytes = image_data.read(10)
                                image_data.seek(0)
                                if first_bytes.startswith(b'<!DOCTYPE') or first_bytes.startswith(b'<html'):
                                    raise ValueError("Downloaded content appears to be HTML")

                            # Convert to WebP
                            if not convert_any_image_to_webp(image_data, file_path):
                                filename_display = file_path.name
                                tqdm.write(f"  X FAILED: {filename_display} ({product_name[:30]}{'...' if len(product_name) > 30 else ''}) - WebP conversion failed")
                                failed_count += 1
                                failed_urls.append((image_url, "WebP conversion failed"))
                                pbar.update(1)
                                continue

                            # Success
                            downloaded_count += 1
                            filename_display = file_path.name
                            tqdm.write(f"  + SUCCESS: {filename_display} ({product_name[:30]}{'...' if len(product_name) > 30 else ''})")
                            pbar.update(1)
                            time.sleep(0.3)

                        except requests.exceptions.RequestException as e:
                            failed_count += 1
                            failed_urls.append((image_url, str(e)))
                            filename_display = file_path.name if 'file_path' in locals() else "unknown"
                            tqdm.write(f"  X FAILED: {filename_display} ({product_name[:30]}{'...' if len(product_name) > 30 else ''}) - {e}")
                            pbar.update(1)
                        except Exception as e:
                            failed_count += 1
                            failed_urls.append((image_url, str(e)))
                            filename_display = file_path.name if 'file_path' in locals() else "unknown"
                            tqdm.write(f"  X ERROR: {filename_display} ({product_name[:30]}{'...' if len(product_name) > 30 else ''}) - {e}")
                            pbar.update(1)

    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file '{csv_file_path}' not found")
    finally:
        session.close()

    # Professional summary
    print(f"\n+ Image downloading complete!")
    print(f"  - Downloaded: {downloaded_count}/{total_images} images")
    if skipped_count > 0:
        print(f"  - Skipped: {skipped_count} (already existed)")
    if failed_count > 0:
        print(f"  - Failed: {failed_count}")
    
    if failed_urls:
        print(f"\n! Failed downloads:")
        for url, err in failed_urls[:5]:  # Show first 5 errors
            print(f"  - {err}")
        if len(failed_urls) > 5:
            print(f"  ... and {len(failed_urls) - 5} more")
    
    print(f"\n[FOLDER] Images saved to: {download_folder}")

    return {
        'total_images': total_images,
        'downloaded': downloaded_count,
        'skipped': skipped_count,
        'failed': failed_count,
    }