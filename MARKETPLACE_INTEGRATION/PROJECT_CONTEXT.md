# PROJECT CONTEXT - IntelliScrape Pro Integration

## Current Situation
- **Developer**: Working 2 days/week (college schedule, ~16 hours/week)
- **Timeline**: 8 weeks total (college course ending)
- **Current State**: Standalone Flask web scraper working locally
- **Goal**: Convert to plugin/integration for marketplace (JustSell)
- **Contact**: Development Lead at marketplace (awaiting feedback)
- **Decision**: POPUP WINDOW implementation (based on research - faster, simpler, more secure)

## Marketplace Requirements (from Teams conversation)
1. **API Integration Required**: "It'll most likely need to be connected via API as it will need to update data/save in the database"
2. **UI Must Match**: Must follow Snow UI v2 design system - https://v0.app/chat/duplicate-of-dashboard-redesign-snow-ui-v2-zUQMkgrBqKW
3. **Database Integration**: Data needs to go directly to JustSell database (not CSV downloads)
4. **He requested**: ZIP file of current code for review (sent: IntelliScrape_Pro.zip)

## Integration Options Discussed

### Option 1: POPUP WINDOW (Recommended - Fastest)
**Implementation**:
```javascript
// Marketplace adds one button:
<button onclick="window.open('https://scraper-site.com', 'scraper', 'width=900,height=700')">
  Scrape Products
</button>
```
**Timeline**: 2-3 weeks with AI assistance
**Pros**:
- Zero architecture changes needed
- Works with existing code
- Full screen space for UI
- No cross-domain issues
**Cons**:
- Less integrated feeling
- Popup blockers might interfere

### Option 2: IFRAME INTEGRATION
**Implementation**:
```html
<iframe src="https://scraper-site.com/plugin" width="400" height="500"></iframe>
```
**Timeline**: 6-8 weeks with AI assistance
**Pros**:
- Embedded in marketplace site
- Professional appearance
**Cons**:
- Cross-domain security complexity
- CSS conflicts possible
- Requires UI redesign for small space

### Option 3: API-ONLY INTEGRATION (What marketplace seems to want)
**Implementation**:
- Scraper becomes REST API service
- JustSell builds their own UI
- Data flows: JustSell UI → Scraper API → Return JSON → JustSell Database
**Timeline**: 8-10 weeks
**Pros**:
- Perfect UI integration (they control it)
- Most professional approach
- Scalable
**Cons**:
- Requires complete restructuring
- They need to build UI
- Most complex option

## Current System Architecture

### What We Have:
```
Flask Backend (app.py)
├── API Endpoints:
│   ├── /api/extract-urls (finds product URLs)
│   ├── /api/scrape-products (scrapes product data)
│   ├── /api/job/{id} (check progress)
│   └── /api/download-csv (exports data)
├── Scraping Modules:
│   ├── scraper.py (Firecrawl API integration)
│   ├── product_scraper.py (URL extraction)
│   └── image_downloader.py (NOT INTEGRATED YET)
└── Frontend:
    ├── templates/index.html (single-page app)
    ├── static/js/app.js (2000+ lines)
    └── static/css/style.css (3600+ lines)
```

### Current Data Flow:
```
User Input → Flask Backend → Firecrawl API → Generate CSV → User Downloads
```

### What Marketplace Wants:
```
JustSell UI → Scraper API → Firecrawl → JSON Response → JustSell Database
```

## Critical Missing Features

### 1. IMAGE DOWNLOADING (Not Currently Working!)
**Current**: Only scrapes image URLs (links to images)
**Needed**: Download actual image files and upload to S3
**Complexity**: Additional 4-6 weeks of work
**Issues**:
- Copyright/legal concerns
- Storage costs
- Download failures
- S3 integration needed

### 2. S3 INTEGRATION (Boss Requirement)
**What Boss Wants**:
- Images automatically uploaded to S3
- CSV data with S3 image URLs
- Direct integration with marketplace
**Implementation Needed**:
```python
import boto3
s3_client = boto3.client('s3',
    aws_access_key_id='xxx',
    aws_secret_access_key='xxx'
)
# Upload images during scraping
# Return S3 URLs instead of original URLs
```

### 3. DATABASE INTEGRATION
**Current**: CSV file download only
**Needed**: Direct database insertion
**Questions for Marketplace**:
- What database schema?
- What fields are required?
- How to handle duplicates?
- Authentication method?

## Development Timeline (Realistic with College Schedule)

### Phase 1: Basic Integration (Weeks 1-3)
- [ ] Deploy scraper to live server (DigitalOcean/Heroku)
- [ ] Create popup/iframe version
- [ ] Basic API endpoints working
- [ ] Test with marketplace team

### Phase 2: API Development (Weeks 4-6)
- [ ] Convert to REST API
- [ ] JSON response format
- [ ] Authentication system
- [ ] Rate limiting
- [ ] API documentation

### Phase 3: Image System (Weeks 7-10)
- [ ] Add image downloading
- [ ] S3 integration
- [ ] Error handling
- [ ] Storage optimization

### Phase 4: Database Integration (Weeks 11-12)
- [ ] Schema mapping
- [ ] Direct database writes
- [ ] Duplicate handling
- [ ] Transaction management

### Phase 5: UI Adaptation (Weeks 13-15)
- [ ] Redesign for Snow UI
- [ ] Component matching
- [ ] Testing with JustSell
- [ ] Final integration

## Key Technical Decisions Pending

1. **Hosting**: Where will scraper API live?
   - Options: DigitalOcean, AWS, Heroku, their servers?

2. **Authentication**: How to secure API?
   - API keys? OAuth? JWT tokens?

3. **Image Storage**: Who pays for S3?
   - Their bucket or ours?
   - Who manages credentials?

4. **Scaling**: Expected load?
   - How many concurrent users?
   - Rate limits needed?

5. **Data Format**: Exact schema needed?
   - What fields are required?
   - How to handle missing data?

## API Configuration Required

### Firecrawl API (Required for scraping)
- Current: Using free tier (500 pages/month)
- Cost: ~$50/month for production
- Alternative: BeautifulSoup (less reliable)

### Groq AI (Optional for descriptions)
- Current: Free tier
- Used for: Auto-generating product descriptions
- Alternative: OpenAI API

### AWS S3 (Required for images)
- Not yet implemented
- Cost: ~$0.023 per GB/month storage
- Need: AWS credentials, bucket setup

## Questions to Ask in Next Meeting

1. **Architecture**: "Should the scraper run as separate microservice or integrated into JustSell codebase?"

2. **UI Responsibility**: "Do you want me to build Snow UI compatible frontend, or will your team handle all UI?"

3. **Database Schema**: "What exact fields does your product table require?"

4. **Timeline Priority**: "What's more important - getting basic API working quickly, or waiting for full integration with images/database?"

5. **Deployment**: "Where should the scraper API be hosted? Your infrastructure or separate?"

6. **Authentication**: "How should we handle API authentication between services?"

7. **Costs**: "Who handles API costs (Firecrawl, S3 storage)?"

## Current Blockers

1. **No Live Demo**: Can't show marketplace without deploying online
2. **No API Keys**: Marketplace can't test without Firecrawl key
3. **Image System**: Not built yet, adds significant complexity
4. **UI Mismatch**: Current dark theme vs Snow UI requirement
5. **Database Unknown**: Don't know their schema

## Next Steps (Prioritized)

1. **IMMEDIATE**: Wait for marketplace feedback on ZIP file
2. **This Week**: Deploy to free hosting for demo
3. **Next Session**: Start API conversion based on feedback
4. **Following Week**: Begin image download system if approved

## Code Snippets for Quick Reference

### Current Flask Route Structure:
```python
@app.route('/api/extract-urls', methods=['POST'])
@app.route('/api/scrape-products', methods=['POST'])
@app.route('/api/job/<job_id>')
@app.route('/api/download-csv')
```

### Needed API Structure:
```python
@app.route('/api/v1/scrape', methods=['POST'])
def scrape_products():
    # Authenticate request
    # Validate input
    # Start scraping job
    # Return job ID
    return jsonify({"job_id": job_id, "status": "processing"})

@app.route('/api/v1/results/<job_id>', methods=['GET'])
def get_results():
    # Return scraped data as JSON
    return jsonify({"products": products, "images": s3_urls})
```

### Popup Integration Code:
```javascript
// For marketplace to add
function openScraper() {
    const scraperWindow = window.open(
        'https://scraper-api.com/popup',
        'scraper',
        'width=900,height=700'
    );

    // Listen for completion
    window.addEventListener('message', function(e) {
        if (e.data.type === 'scraping_complete') {
            // Handle scraped data
            processScrapedProducts(e.data.products);
        }
    });
}
```

## Important Notes

- **College Schedule**: Only 2 days/week availability - all timelines account for this
- **AI Assistance**: Using Claude to accelerate development
- **MVP First**: Start with basic functionality, add features incrementally
- **Communication**: Keep marketplace team updated weekly on progress

## File/Folder Structure (Current)
```
FrontEndScraper/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── config/
│   └── .env              # API keys (not in ZIP)
├── templates/
│   └── index.html        # Main UI
├── static/
│   ├── css/style.css     # Styling
│   ├── js/app.js         # Frontend logic
│   └── logo.svg          # Logo
├── ScraperFunctions/
│   └── modules/
│       ├── scraper.py
│       ├── product_scraper.py
│       └── image_downloader.py
└── docs/                  # Documentation files

```

## Development Environment Setup

```bash
# Required
Python 3.9+
pip install -r requirements.txt

# Environment variables needed
FIRECRAWL_API_KEY=fc-xxxxx
GROQ_API_KEY=gsk_xxxxx (optional)
AWS_ACCESS_KEY_ID=xxxxx (future)
AWS_SECRET_ACCESS_KEY=xxxxx (future)

# Run locally
python app.py
# Access at http://localhost:5000
```

---
Last Updated: September 24, 2024
Next Review: After marketplace feedback