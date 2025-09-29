# Digital Ocean Deployment Guide for MarketPlace Scraper Pro

## Prerequisites
- Digital Ocean account
- Domain name (optional, but recommended)
- API Keys ready (Firecrawl, Groq)

---

## Step 1: Create a Digital Ocean Droplet

### 1.1 Log into Digital Ocean
- Go to https://cloud.digitalocean.com/

### 1.2 Create New Droplet
1. Click "Create" → "Droplets"
2. Choose an image: **Ubuntu 22.04 LTS**
3. Choose a plan:
   - **Recommended**: Basic Plan
   - **Size**: $12/month (2GB RAM, 2 vCPUs) minimum
   - For production: $24/month (4GB RAM, 2 vCPUs)
4. Choose datacenter: Select closest to your users
5. Authentication: Choose **SSH keys** (more secure) or Password
6. Hostname: `marketplace-scraper` or your preference
7. Click "Create Droplet"

---

## Step 2: Initial Server Setup

### 2.1 Connect to Your Droplet
```bash
ssh root@your-droplet-ip
```

### 2.2 Update System
```bash
apt update && apt upgrade -y
```

### 2.3 Create a New User (Security Best Practice)
```bash
adduser scraper
usermod -aG sudo scraper
```

### 2.4 Set up Firewall
```bash
ufw allow OpenSSH
ufw allow 5000  # For Flask development
ufw allow 80    # For HTTP
ufw allow 443   # For HTTPS
ufw enable
```

---

## Step 3: Install Required Software

### 3.1 Install Python and Dependencies
```bash
# Install Python 3.10+ and pip
apt install python3-pip python3-venv python3-dev -y

# Install build essentials
apt install build-essential libssl-dev libffi-dev -y

# Install nginx for production
apt install nginx -y

# Install git
apt install git -y
```

### 3.2 Install Node.js (for any JS dependencies)
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt install nodejs -y
```

---

## Step 4: Clone and Setup Your Application

### 4.1 Switch to the scraper user
```bash
su - scraper
```

### 4.2 Clone Your Repository
```bash
cd /home/scraper
git clone https://github.com/yourusername/FrontEndScraper.git
cd FrontEndScraper
```

**OR** Upload files via SFTP/SCP:
```bash
# From your local machine
scp -r /path/to/FrontEndScraper scraper@your-droplet-ip:/home/scraper/
```

### 4.3 Create Python Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4.4 Install Python Requirements
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 5: Configure Your Application

### 5.1 Create Environment File
```bash
nano .env
```

Add your API keys:
```env
FIRECRAWL_API_KEY=your_firecrawl_key_here
GROQ_API_KEY=your_groq_key_here
FLASK_ENV=production
FLASK_DEBUG=False
```

### 5.2 Create Required Directories
```bash
# Ensure all required directories exist
mkdir -p ScraperFunctions/data
mkdir -p ScraperFunctions/downloaded_images
mkdir -p ScraperFunctions/print_ready_images
mkdir -p ScraperFunctions/temp
```

### 5.3 Set Permissions
```bash
chmod -R 755 /home/scraper/FrontEndScraper
chmod -R 777 ScraperFunctions/data  # For CSV writing
chmod -R 777 ScraperFunctions/downloaded_images
chmod -R 777 ScraperFunctions/temp
```

---

## Step 6: Test Your Application

### 6.1 Run Flask in Development Mode (for testing)
```bash
source venv/bin/activate
python app.py
```

Visit `http://your-droplet-ip:5000` to test.

**If it works, press Ctrl+C to stop.**

---

## Step 7: Setup Production Server with Gunicorn

### 7.1 Install Gunicorn
```bash
pip install gunicorn
```

### 7.2 Create Gunicorn Service File
```bash
sudo nano /etc/systemd/system/scraper.service
```

Add this content:
```ini
[Unit]
Description=MarketPlace Scraper Pro
After=network.target

[Service]
User=scraper
Group=scraper
WorkingDirectory=/home/scraper/FrontEndScraper
Environment="PATH=/home/scraper/FrontEndScraper/venv/bin"
ExecStart=/home/scraper/FrontEndScraper/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 300 app:app

Restart=always

[Install]
WantedBy=multi-user.target
```

### 7.3 Start and Enable Service
```bash
sudo systemctl start scraper
sudo systemctl enable scraper
sudo systemctl status scraper  # Check if running
```

---

## Step 8: Configure Nginx as Reverse Proxy

### 8.1 Create Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/scraper
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com your-droplet-ip;

    client_max_body_size 100M;
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/scraper/FrontEndScraper/static;
        expires 30d;
    }
}
```

### 8.2 Enable the Site
```bash
sudo ln -s /etc/nginx/sites-available/scraper /etc/nginx/sites-enabled
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

---

## Step 9: Setup SSL Certificate (HTTPS)

### 9.1 Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### 9.2 Get SSL Certificate
```bash
sudo certbot --nginx -d your-domain.com
```

Follow the prompts to configure HTTPS automatically.

---

## Step 10: Important Files and Folders Checklist

### Required Files for Deployment:
```
FrontEndScraper/
├── app.py                          # Main Flask application [REQUIRED]
├── requirements.txt                # Python dependencies [REQUIRED]
├── .env                           # API keys and config [CREATE ON SERVER]
│
├── templates/                     # HTML templates [REQUIRED]
│   └── index.html                # Main interface
│
├── static/                        # Static files [REQUIRED]
│   ├── css/
│   │   └── style.css            # Styles
│   └── js/
│       └── app.js               # Frontend JavaScript
│
└── ScraperFunctions/             # Scraping modules [REQUIRED]
    ├── modules/                  # Python modules [REQUIRED]
    │   ├── scraper.py           # Core scraper
    │   ├── product_scraper.py   # Product scraper
    │   └── image_downloader.py  # Image handler
    │
    ├── brand_config.json        # Brand configuration [REQUIRED]
    │
    └── data/                    # Data directory [CREATE WITH PERMISSIONS]
        └── products.csv         # Will be created automatically
```

### Files NOT needed for deployment:
- Test files (test_*.py)
- .git directory (if uploading manually)
- __pycache__ directories
- *.pyc files
- Local virtual environment (venv/)

---

## Step 11: Create requirements.txt

Make sure your `requirements.txt` includes:
```txt
Flask==2.3.2
flask-cors==4.0.0
python-dotenv==1.0.0
firecrawl-py==0.0.10
beautifulsoup4==4.12.2
requests==2.31.0
tqdm==4.65.0
Pillow==10.0.0
groq==0.4.2
pandas==2.0.3
openpyxl==3.1.2
gunicorn==21.2.0
```

---

## Step 12: Monitoring and Maintenance

### 12.1 View Application Logs
```bash
# View service logs
sudo journalctl -u scraper -f

# View Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### 12.2 Restart Services
```bash
# Restart your app
sudo systemctl restart scraper

# Restart Nginx
sudo systemctl restart nginx
```

### 12.3 Update Application
```bash
cd /home/scraper/FrontEndScraper
git pull  # If using git
source venv/bin/activate
pip install -r requirements.txt  # Update dependencies
sudo systemctl restart scraper
```

---

## Step 13: Production Optimizations

### 13.1 Update app.py for Production
Add this at the top of app.py:
```python
import os

# Production settings
if os.environ.get('FLASK_ENV') == 'production':
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
```

### 13.2 Set Up Automated Backups
```bash
# Create backup script
nano /home/scraper/backup.sh
```

Add:
```bash
#!/bin/bash
tar -czf /home/scraper/backups/scraper_$(date +%Y%m%d).tar.gz /home/scraper/FrontEndScraper/ScraperFunctions/data/
find /home/scraper/backups/ -name "*.tar.gz" -mtime +7 -delete
```

Make it executable and add to cron:
```bash
chmod +x /home/scraper/backup.sh
crontab -e
# Add: 0 2 * * * /home/scraper/backup.sh
```

---

## Step 14: Security Recommendations

1. **Use Environment Variables**: Never commit API keys to git
2. **Regular Updates**:
   ```bash
   apt update && apt upgrade -y  # Monthly
   ```
3. **Monitor Disk Space**:
   ```bash
   df -h  # Check disk usage
   ```
4. **Set up Fail2ban** (optional):
   ```bash
   apt install fail2ban -y
   ```

---

## Step 15: Testing Your Deployment

### Test Checklist:
- [ ] Visit http://your-droplet-ip - should show your app
- [ ] Test URL extraction with a real website
- [ ] Test product scraping with real URLs
- [ ] Check CSV download functionality
- [ ] Verify API key validation works
- [ ] Test both WSMarketplace and JustSell modes
- [ ] Check that scraped data persists

---

## Troubleshooting Common Issues

### Issue: "502 Bad Gateway"
```bash
sudo systemctl status scraper  # Check if service is running
sudo systemctl restart scraper  # Restart service
```

### Issue: "Permission Denied" when writing files
```bash
sudo chown -R scraper:scraper /home/scraper/FrontEndScraper
chmod -R 777 ScraperFunctions/data
chmod -R 777 ScraperFunctions/downloaded_images
```

### Issue: Application not starting
```bash
# Check logs
sudo journalctl -u scraper -n 50

# Test manually
cd /home/scraper/FrontEndScraper
source venv/bin/activate
python app.py  # See error messages
```

### Issue: Can't connect to droplet
```bash
# Check firewall
sudo ufw status
sudo ufw allow 80
sudo ufw allow 443
```

---

## Quick Deployment Commands Summary

```bash
# One-liner to check everything is running
sudo systemctl status scraper nginx | grep Active

# Full restart
sudo systemctl restart scraper nginx

# View recent logs
sudo journalctl -u scraper --since "1 hour ago"

# Monitor real-time
sudo journalctl -u scraper -f
```

---

## Estimated Deployment Time
- Initial setup: 30-45 minutes
- Testing and verification: 15-20 minutes
- Total: ~1 hour

## Monthly Costs
- Droplet: $12-24/month
- Domain (optional): $10-15/year
- SSL Certificate: Free with Let's Encrypt

---

## Support Resources
- Digital Ocean Documentation: https://docs.digitalocean.com/
- Flask Deployment: https://flask.palletsprojects.com/deploying/
- Nginx Documentation: https://nginx.org/en/docs/

---

## Final Notes
1. Always test in development mode first before switching to production
2. Keep backups of your products.csv file
3. Monitor your API usage (Firecrawl has limits)
4. Set up alerts for disk space and CPU usage in Digital Ocean dashboard

Good luck with your deployment! 🚀