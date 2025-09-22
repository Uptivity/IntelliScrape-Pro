# IntelliScrape Pro - Enterprise Web Scraping Platform

> **Note:** This is a documentation repository. The source code is proprietary and maintained in a private repository.

## Project Status
- **Source Code**: Private/Proprietary
- **Documentation**: Public
- **Development**: Active
- **Version**: 2.0

---

## Overview

IntelliScrape Pro is an enterprise-grade web scraping platform designed for e-commerce data extraction. The application provides automated product discovery, comprehensive data extraction, and AI-powered content generation capabilities.

### Key Features

- **Automated URL Discovery**: Extract product URLs from category and homepage listings
- **Comprehensive Data Extraction**: Capture product names, prices, descriptions, images, and specifications
- **AI-Powered Enhancement**: Generate product descriptions and SKUs using Groq AI
- **Session Management**: Track and organize multiple scraping sessions
- **Multiple Export Formats**: CSV, Excel, JSON with platform-specific formatting
- **Real-time Progress Tracking**: Monitor extraction progress with detailed metrics

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.9+, Flask 2.0+ |
| **Frontend** | HTML5, CSS3, JavaScript ES6+ |
| **Scraping Engine** | Firecrawl API, BeautifulSoup4 |
| **AI Integration** | Groq AI (Llama 3.1) |
| **Data Formats** | CSV, JSON, Excel |

---

## System Requirements

- Python 3.9 or higher
- 4GB RAM minimum
- Active internet connection
- Firecrawl API key (required)
- Groq AI API key (optional)

---

## Installation Guide

### 1. Clone Repository
```bash
git clone [repository-url]
cd intelliscrape-pro
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```
FIRECRAWL_API_KEY=your_firecrawl_key
GROQ_API_KEY=your_groq_key
```

### 5. Launch Application
```bash
python app.py
```

Access the application at `http://localhost:5000`

---

## User Guide

### Getting Started with API Keys

#### Firecrawl API (Required)
1. Visit [Firecrawl.dev](https://www.firecrawl.dev)
2. Create an account
3. Navigate to API Keys section
4. Generate and copy your API key
5. Add to Settings in the application

#### Groq AI API (Optional)
1. Visit [Groq Console](https://console.groq.com)
2. Register for an account
3. Generate an API key
4. Add to Settings if using auto-generation features

### Scraping Workflow

#### Phase 1: URL Discovery
1. Enter homepage or category URLs
2. Click "Initialize Extraction"
3. System automatically discovers product URLs
4. Review and edit discovered URLs as needed

#### Phase 2: Data Extraction
1. Confirm or paste product URLs
2. Configure extraction settings
3. Click "Begin Scraping"
4. Monitor real-time progress
5. View results in data table

#### Phase 3: Data Management
1. Edit individual cells by clicking
2. Apply bulk operations via Quick Actions
3. Export data in desired format
4. Finalize session for archival

---

## Configuration Options

### Application Settings
- **Timeout**: Request timeout duration (default: 30 seconds)
- **Max Products**: Maximum products per session (default: 50)
- **Auto-Generate SKU**: Enable automatic SKU generation
- **Auto-Generate Description**: Enable AI description generation

### Field Selection
Configure which data fields to extract:
- Product Name (required)
- SKU (required)
- Category
- Brand
- Pricing Information
- Stock Levels
- Specifications
- Product Images

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extract-urls` | POST | Discover product URLs from homepage |
| `/api/scrape-products` | POST | Extract product details |
| `/api/job/{job_id}` | GET | Check job status |
| `/api/validate-key` | POST | Validate API keys |
| `/api/download-csv` | GET | Export scraped data |
| `/api/status` | GET | System status check |

---

## Troubleshooting

### Common Issues

**API Key Validation Failed**
- Verify the complete key is copied without spaces
- Check account status on provider's dashboard
- Generate a new key if necessary

**No Products Found**
- Confirm website is e-commerce platform
- Try different category or listing page
- Check if site requires authentication

**SKU Generation Not Working**
- Enable Auto-Generate SKU in Settings
- Ensure products have valid names
- Check browser console for errors

**Extraction Timeout**
- Increase timeout value in Settings
- Check internet connection stability
- Verify API service status

---

## Frequently Asked Questions

**Q: What websites are supported?**
A: The platform works best with standard e-commerce sites built on Shopify, WooCommerce, Magento, and similar platforms.

**Q: What are the extraction limits?**
A: Limits depend on your Firecrawl API tier. Free tier typically allows 500 pages per month.

**Q: Can I resume interrupted sessions?**
A: Yes, enable "Auto-save progress" in Settings to save progress every 10 products.

**Q: Which export format should I use?**
A: CSV for universal compatibility, Excel for manual editing, JSON for API integrations.

**Q: Is batch processing supported?**
A: Yes, you can process multiple URLs simultaneously and apply bulk operations to results.

---

## Performance Optimization

### Best Practices
- Process URLs in batches of 20-30 for optimal performance
- Enable auto-save for large extraction sessions
- Use specific category pages rather than entire site maps
- Configure appropriate timeout values based on target site

### Rate Limiting
- Default: 2 requests per second
- Adjustable based on API tier
- Automatic retry on rate limit errors

---

## Data Privacy & Security

- API keys are stored locally in browser storage
- No data is transmitted to third parties except configured APIs
- Session data can be exported and deleted at any time
- All API communications use HTTPS encryption

---

## System Architecture

```
Frontend (Browser)
    ├── User Interface (HTML/CSS/JS)
    ├── Session Management
    └── Real-time Updates
         |
    Flask Server
    ├── API Routes
    ├── Job Queue Management
    └── Data Processing
         |
    External APIs
    ├── Firecrawl (Scraping)
    └── Groq AI (Enhancement)
```

---

## Version History

- **v2.0** - Current version with AI integration and session management
- **v1.5** - Added bulk operations and field selection
- **v1.0** - Initial release with basic scraping functionality

---

## License

This software is proprietary and confidential. All rights reserved.

---

## Contact & Support

For technical support or inquiries, please contact the development team through internal channels.

**Last Updated:** January 2025
