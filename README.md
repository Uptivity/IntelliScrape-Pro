# IntelliScrape Pro - User Guide

## Overview

IntelliScrape Pro is a web-based tool for extracting product data from e-commerce websites. This guide will help you navigate and use the platform effectively.

---

## Getting Started

### First-Time Setup

1. **Access the Platform**
   - Open your web browser
   - Navigate to the IntelliScrape Pro URL
   - Bookmark the page for easy access

2. **Configure Your API Keys**
   - Click the Settings button in the header
   - Enter your Firecrawl API key (required)
   - Enter your Groq AI key (optional, for AI features)
   - Click Save Settings

### Obtaining API Keys

**Firecrawl API Key (Required)**
- Visit https://www.firecrawl.dev
- Sign up for a free account
- Go to your dashboard → API Keys
- Copy the key and paste in Settings

**Groq AI Key (Optional)**
- Visit https://console.groq.com
- Create a free account
- Navigate to API Keys
- Generate and copy your key

---

## How to Scrape Products

### Step 1: Extract Product URLs

1. In the "URL Discovery" section, enter homepage or category URLs
2. Enter one URL per line
3. Click "Initialize Extraction"
4. Wait for the system to find product URLs
5. Review the discovered URLs in the results box

### Step 2: Scrape Product Data

1. Product URLs will auto-populate from Step 1
2. Or paste your own product URLs directly
3. Click "Begin Scraping"
4. Watch the progress bar for real-time updates
5. Products will appear in the table below when complete

### Step 3: Review and Edit

1. Click any cell in the results table to edit
2. Use Quick Actions buttons for bulk updates:
   - Set all stock levels
   - Apply markup to prices
   - Activate all products

### Step 4: Export Your Data

1. Click "Finalize Session"
2. Choose your export format:
   - CSV - Universal spreadsheet format
   - Excel - For Microsoft Excel
   - JSON - For developers
3. File will download to your computer

---

## Features Guide

### Session Management
- **Active Session**: Your current working session
- **Completed Sessions**: View past scraping sessions
- **Auto-save**: Enable in Settings to save progress automatically

### Advanced Configuration
Click "Advanced Configuration" to customize:
- Which fields to extract
- Default values for stock and status
- Field selection for different platforms

### Quick Actions
- **Set Stock**: Apply the same stock level to all products
- **Apply Markup**: Add percentage markup to wholesale prices
- **Activate All**: Set all products to active status

### Settings Options
- **Timeout**: How long to wait for each page (default: 30 seconds)
- **Max Products**: Limit per session (default: 50)
- **Auto-Generate SKU**: Create product codes automatically
- **Auto-Generate Description**: Use AI to write descriptions

---

## Troubleshooting

### "API Key Invalid"
- Check you copied the complete key
- Make sure there are no spaces
- Try generating a new key from your provider

### "No Products Found"
- Verify the URL is a product listing or category page
- Try a different page from the same website
- Some sites may have anti-scraping protection

### Products Not Appearing
- Check the API Status indicator (should show "Online")
- Verify your internet connection
- Refresh the page and try again

### Can't Export Data
- Make sure you have at least one product scraped
- Check browser popup blocker settings
- Try a different export format

### Session Not Saving
- Enable "Auto-save progress" in Settings
- Check browser local storage is enabled
- Don't use private/incognito mode

---

## Tips for Best Results

1. **Start Small**: Test with 5-10 products first
2. **Use Category Pages**: More reliable than homepage URLs
3. **Check API Status**: Green means ready to scrape
4. **Save Regularly**: Use auto-save for large batches
5. **Edit Before Export**: Review and clean data in the table

---

## Understanding the Interface

### Header Bar
- **API Status**: Shows if services are connected
- **Module Status**: Shows if scraper is ready
- **Dark Mode**: Toggle for comfortable viewing

### Progress Indicators
- **Progress Bar**: Shows completion percentage
- **Status Text**: Current operation details
- **Time Estimates**: Expected completion time
- **Processing Speed**: Items per minute

### Results Table
- **Editable Cells**: Click to modify any value
- **Auto-save**: Changes are saved automatically
- **Sorting**: Click column headers to sort

---

## Export Formats Explained

**CSV Format**
- Opens in Excel, Google Sheets
- Best for general use
- Compatible with most systems

**Excel Format**
- Native Excel file
- Preserves formatting
- Best for Excel users

**JSON Format**
- For developers and APIs
- Structured data format
- Best for integrations

---

## Frequently Asked Questions

**How many products can I scrape?**
Free tier allows approximately 500 products per month.

**Can I pause and resume?**
Enable auto-save in Settings. Your progress saves every 10 products.

**Why is scraping slow?**
Speed depends on the target website and API limits. Normal speed is 2-3 products per second.

**Can I scrape any website?**
Works best with standard e-commerce sites. Some sites with protection may not work.

**Is my data private?**
All data stays in your browser. Only API keys are used for external services.

**How do I scrape multiple sites?**
Complete one site, export data, then start a new session for the next site.

---

## Quick Reference

### Keyboard Shortcuts
- **Enter**: Save cell edit
- **Escape**: Cancel cell edit
- **Tab**: Move to next cell

### Status Indicators
- **Green**: System ready
- **Yellow**: Processing
- **Red**: Error or offline

### Session States
- **Active**: Currently working
- **Completed**: Finished and exported
- **Auto-saved**: Partially complete

---

## Need Help?

If you encounter issues not covered in this guide:

1. Check the API Status indicator
2. Refresh the page
3. Clear browser cache
4. Try a different browser
5. Verify API keys are valid

---

**Version 2.0** | Last Updated: January 2025
