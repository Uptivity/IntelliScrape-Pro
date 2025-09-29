# 8-WEEK POPUP INTEGRATION GUIDE
## From Localhost to Live Marketplace Integration

---

## WEEK 1-2: DEPLOYMENT & BASIC SETUP

### Day 1-2: Deploy to Live Server

#### Option A: Render.com (Recommended - Free)
```bash
# 1. Add gunicorn to requirements.txt
echo "gunicorn==21.2.0" >> requirements.txt

# 2. Push to GitHub
git add .
git commit -m "Add deployment config"
git push

# 3. Connect Render to GitHub
# - Go to render.com
# - New > Web Service
# - Connect GitHub repo
# - Use render.yaml settings
# - Add environment variables in dashboard
```

Your live URL will be: `https://intelliscrape-pro.onrender.com`

#### Option B: DigitalOcean (More control - $6/month)
```bash
# 1. Create droplet (Ubuntu 22.04)
# 2. SSH into server
ssh root@your-server-ip

# 3. Setup Python environment
apt update && apt upgrade -y
apt install python3-pip python3-venv nginx -y

# 4. Clone your repo
git clone https://github.com/yourusername/intelliscrape.git
cd intelliscrape

# 5. Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. Setup systemd service
sudo nano /etc/systemd/system/intelliscrape.service
```

### Day 3-4: Create Popup-Specific Route

Add to `app.py`:
```python
@app.route('/popup')
def popup_interface():
    """Optimized interface for popup mode"""
    marketplace_origin = request.args.get('origin', '*')
    return render_template('popup.html',
                         marketplace_origin=marketplace_origin,
                         compact_mode=True)

@app.route('/api/popup/complete', methods=['POST'])
def popup_complete():
    """Send scraped data back to parent window"""
    data = request.json
    # Process and return formatted data
    return jsonify({
        "status": "success",
        "products": data.get('products', []),
        "job_id": data.get('job_id')
    })
```

---

## WEEK 3-4: POPUP COMMUNICATION SYSTEM

### Create `templates/popup.html`:
```html
<!DOCTYPE html>
<html>
<head>
    <title>IntelliScrape Pro - Popup Mode</title>
    <link rel="stylesheet" href="/static/css/popup-style.css">
</head>
<body>
    <div id="popup-app">
        <header>
            <h2>Product Scraper</h2>
            <button onclick="window.close()" class="close-btn">×</button>
        </header>

        <div class="scraper-content">
            <!-- Your existing scraper UI here, simplified -->
        </div>
    </div>

    <script>
        // Communication with parent window
        const MARKETPLACE_ORIGIN = '{{ marketplace_origin }}';

        function sendToParent(data) {
            if (window.opener) {
                window.opener.postMessage({
                    type: 'SCRAPER_DATA',
                    payload: data
                }, MARKETPLACE_ORIGIN);
            }
        }

        // When scraping completes
        function onScrapingComplete(products) {
            sendToParent({
                status: 'complete',
                products: products,
                timestamp: new Date().toISOString()
            });

            // Optional: Show success message
            alert('Data sent to marketplace! You can close this window.');
        }

        // Handle errors
        window.onerror = function(msg, url, line) {
            sendToParent({
                status: 'error',
                message: msg
            });
        };
    </script>
</body>
</html>
```

### Create Integration Script for Marketplace:
```javascript
// marketplace-integration.js - Give this to Kieran
(function() {
    // Configuration
    const SCRAPER_URL = 'https://intelliscrape-pro.onrender.com/popup';
    const MARKETPLACE_API = 'https://justsell.com/api/products/import';

    // Add scraper button to marketplace
    function addScraperButton() {
        const button = document.createElement('button');
        button.innerText = '🔍 Scrape Products';
        button.className = 'scraper-btn';
        button.onclick = openScraper;

        // Find appropriate place in marketplace UI
        const toolbar = document.querySelector('.product-toolbar') ||
                       document.querySelector('.actions') ||
                       document.body;
        toolbar.appendChild(button);
    }

    // Open scraper popup
    function openScraper() {
        const width = 900;
        const height = 700;
        const left = (screen.width - width) / 2;
        const top = (screen.height - height) / 2;

        const popup = window.open(
            `${SCRAPER_URL}?origin=${encodeURIComponent(window.location.origin)}`,
            'intelliscrape',
            `width=${width},height=${height},left=${left},top=${top},` +
            'toolbar=no,menubar=no,scrollbars=yes,resizable=yes'
        );

        // Check if popup was blocked
        if (!popup || popup.closed || typeof popup.closed == 'undefined') {
            alert('Please allow popups for this site to use the scraper.');
        }
    }

    // Listen for data from scraper
    window.addEventListener('message', function(event) {
        // Verify origin
        if (event.origin !== new URL(SCRAPER_URL).origin) return;

        // Handle scraper messages
        if (event.data && event.data.type === 'SCRAPER_DATA') {
            handleScrapedData(event.data.payload);
        }
    });

    // Process scraped data
    function handleScrapedData(data) {
        if (data.status === 'complete') {
            // Send to marketplace API
            fetch(MARKETPLACE_API, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + getAuthToken()
                },
                body: JSON.stringify({
                    products: data.products,
                    source: 'intelliscrape',
                    timestamp: data.timestamp
                })
            })
            .then(response => response.json())
            .then(result => {
                alert(`Successfully imported ${result.count} products!`);
                // Refresh product list
                if (window.refreshProductList) {
                    window.refreshProductList();
                }
            })
            .catch(error => {
                console.error('Import failed:', error);
                alert('Failed to import products. Please try again.');
            });
        } else if (data.status === 'error') {
            console.error('Scraper error:', data.message);
            alert('Scraping failed: ' + data.message);
        }
    }

    // Get marketplace auth token
    function getAuthToken() {
        // This depends on how marketplace stores auth
        return localStorage.getItem('auth_token') ||
               sessionStorage.getItem('auth_token') ||
               document.querySelector('meta[name="csrf-token"]')?.content;
    }

    // Initialize on page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addScraperButton);
    } else {
        addScraperButton();
    }
})();
```

---

## WEEK 5-6: API INTEGRATION & DATA HANDLING

### Add API Endpoints to `app.py`:
```python
from flask_cors import CORS
from functools import wraps
import jwt

# Enable CORS for marketplace
CORS(app, origins=['https://justsell.com', 'https://*.justsell.com'])

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != os.getenv('MARKETPLACE_API_KEY'):
            return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/v1/scrape', methods=['POST'])
@require_api_key
def api_scrape():
    """API endpoint for marketplace integration"""
    data = request.json
    urls = data.get('urls', [])

    # Start scraping job
    job_id = str(uuid.uuid4())
    job = ScraperJob(job_id, "api_scraping")
    jobs[job_id] = job

    # Run in background
    thread = threading.Thread(target=run_scraping, args=(job, urls))
    thread.start()

    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'check_url': f'/api/v1/status/{job_id}'
    })

@app.route('/api/v1/status/<job_id>', methods=['GET'])
@require_api_key
def api_status(job_id):
    """Check scraping job status"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404

    response = {
        'job_id': job_id,
        'status': job.status,
        'progress': f"{job.progress}/{job.total}",
        'message': job.message
    }

    if job.status == 'completed':
        response['data'] = job.result
    elif job.status == 'failed':
        response['error'] = job.error

    return jsonify(response)
```

---

## WEEK 7-8: TESTING & PRODUCTION READY

### Testing Checklist:
```markdown
- [ ] Popup opens correctly from marketplace
- [ ] Data passes back to parent window
- [ ] API authentication works
- [ ] Error handling for failed scrapes
- [ ] Popup blocker detection
- [ ] Mobile fallback (open in new tab)
- [ ] Rate limiting implemented
- [ ] CORS properly configured
- [ ] SSL certificate working
- [ ] Load testing completed
```

### Production Deployment Script:
```bash
#!/bin/bash
# deploy.sh

# Pull latest code
git pull origin main

# Install/update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run migrations if any
python migrate.py

# Restart service
sudo systemctl restart intelliscrape

# Check status
sudo systemctl status intelliscrape

# Run health check
curl https://your-domain.com/api/status
```

### Monitoring Setup:
```python
# Add to app.py
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        # Check Firecrawl API
        # Check disk space
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500
```

---

## MARKETPLACE INTEGRATION CHECKLIST

### For You to Complete:
1. ✅ Deploy scraper to live URL
2. ✅ Create popup-optimized route
3. ✅ Implement postMessage communication
4. ✅ Add API endpoints with authentication
5. ✅ Test with sample marketplace page
6. ✅ Create integration documentation

### For Kieran to Implement:
1. ✅ Add integration script to marketplace
2. ✅ Configure API endpoints
3. ✅ Add scraper button to UI
4. ✅ Handle imported data
5. ✅ Test in staging environment
6. ✅ Deploy to production

---

## QUICK START COMMANDS

```bash
# Week 1: Deploy
git push heroku main

# Week 2: Test popup locally
python app.py
# Open http://localhost:5000/popup

# Week 3-4: Test communication
# Open browser console:
window.postMessage({test: 'data'}, '*')

# Week 5-6: Test API
curl -X POST https://your-site.com/api/v1/scrape \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"]}'

# Week 7-8: Monitor
curl https://your-site.com/health
```

---

## FALLBACK PLAN

If popup blockers become an issue:
1. Detect blocked popup
2. Show modal with options:
   - "Open in new tab" button
   - Instructions to allow popups
   - Alternative: Embedded iframe (if time permits)

```javascript
if (!popup || popup.closed) {
    // Fallback UI
    showModal({
        title: 'Popup Blocked',
        message: 'Please allow popups or',
        buttons: [
            {text: 'Open in New Tab', action: () => window.open(SCRAPER_URL)},
            {text: 'Copy Link', action: () => copyToClipboard(SCRAPER_URL)}
        ]
    });
}
```

---

## ESTIMATED TIMELINE

| Week | Days | Task | Deliverable |
|------|------|------|-------------|
| 1 | 1-2 | Deploy to Render | Live URL |
| 2 | 3-4 | Create popup route | `/popup` endpoint |
| 3 | 5-6 | PostMessage setup | Communication working |
| 4 | 7-8 | Integration script | `marketplace-integration.js` |
| 5 | 9-10 | API endpoints | REST API ready |
| 6 | 11-12 | Authentication | Secure API |
| 7 | 13-14 | Testing | All tests passing |
| 8 | 15-16 | Production ready | Final deployment |

---

## SUCCESS METRICS

- Popup opens in < 2 seconds
- Data transfer successful 95%+ of time
- API response time < 500ms
- Zero security vulnerabilities
- Works on Chrome, Firefox, Safari, Edge
- Mobile fallback functioning