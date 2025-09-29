# Quick Deployment Checklist for Digital Ocean

## Pre-Deployment Checklist
- [ ] Have your Firecrawl API key ready
- [ ] Have your Groq API key ready (optional)
- [ ] Have your Digital Ocean account
- [ ] Have SSH client installed (PuTTY for Windows, Terminal for Mac/Linux)

## Files to Deploy (REQUIRED)
```
✅ app.py                    - Main Flask application
✅ requirements.txt          - Python dependencies
✅ templates/index.html      - Web interface
✅ static/css/style.css      - Styling
✅ static/js/app.js          - Frontend JavaScript
✅ ScraperFunctions/modules/scraper.py
✅ ScraperFunctions/modules/product_scraper.py
✅ ScraperFunctions/modules/image_downloader.py
✅ ScraperFunctions/brand_config.json
```

## Files NOT to Upload
```
❌ test_*.py files
❌ .env (create this on server)
❌ __pycache__ folders
❌ *.pyc files
❌ .git folder (unless using git)
❌ ScraperFunctions/data/*.csv (will be created)
```

## Quick Setup Commands (Copy-Paste Ready)

### 1. Connect to Droplet
```bash
ssh root@YOUR_DROPLET_IP
```

### 2. Quick Setup Script (Run as root)
```bash
# Update system
apt update && apt upgrade -y

# Install requirements
apt install python3-pip python3-venv nginx git -y

# Create user
adduser scraper --gecos "" --disabled-password
echo "scraper:YourPasswordHere" | chpasswd
usermod -aG sudo scraper

# Setup firewall
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable

# Switch to scraper user
su - scraper
```

### 3. Install Application (Run as scraper user)
```bash
# Clone or upload your code
cd ~
# Option 1: Git clone
git clone https://github.com/yourusername/FrontEndScraper.git

# Option 2: Or upload via SFTP (from your local machine)
# scp -r /path/to/FrontEndScraper scraper@YOUR_DROPLET_IP:~/

# Enter directory
cd FrontEndScraper

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
FIRECRAWL_API_KEY=your_firecrawl_key_here
GROQ_API_KEY=your_groq_key_here
FLASK_ENV=production
EOF

# Create data directories
mkdir -p ScraperFunctions/data
mkdir -p ScraperFunctions/downloaded_images
mkdir -p ScraperFunctions/temp

# Set permissions
chmod -R 777 ScraperFunctions/data
chmod -R 777 ScraperFunctions/downloaded_images
chmod -R 777 ScraperFunctions/temp
```

### 4. Test the Application
```bash
# Quick test
python app.py

# If it works, press Ctrl+C to stop
# Visit: http://YOUR_DROPLET_IP:5000
```

### 5. Setup Production Server (Run as scraper user)
```bash
# Install gunicorn
pip install gunicorn

# Exit to root user
exit

# Create service file (as root)
cat > /etc/systemd/system/scraper.service << EOF
[Unit]
Description=MarketPlace Scraper Pro
After=network.target

[Service]
User=scraper
WorkingDirectory=/home/scraper/FrontEndScraper
Environment="PATH=/home/scraper/FrontEndScraper/venv/bin"
ExecStart=/home/scraper/FrontEndScraper/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 300 app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl start scraper
systemctl enable scraper
```

### 6. Setup Nginx (Run as root)
```bash
# Create Nginx config
cat > /etc/nginx/sites-available/scraper << EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;
    proxy_read_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /static {
        alias /home/scraper/FrontEndScraper/static;
        expires 30d;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/scraper /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx
```

### 7. Your App is Live!
Visit: `http://YOUR_DROPLET_IP`

## Verify Everything Works
- [ ] Can access the web interface
- [ ] Can enter API keys in settings
- [ ] Can extract URLs from a website
- [ ] Can scrape product details
- [ ] Can download CSV file
- [ ] Both JustSell and WSMarketplace modes work

## Monitoring Commands
```bash
# Check if services are running
systemctl status scraper
systemctl status nginx

# View logs
journalctl -u scraper -f

# Restart if needed
systemctl restart scraper
systemctl restart nginx
```

## Common Fixes

### If site shows "502 Bad Gateway"
```bash
systemctl restart scraper
```

### If can't write CSV files
```bash
chmod -R 777 /home/scraper/FrontEndScraper/ScraperFunctions/data
```

### If changes don't appear
```bash
# Clear browser cache (Ctrl+F5)
# Or restart services
systemctl restart scraper nginx
```

## Update Your App Later
```bash
cd /home/scraper/FrontEndScraper
git pull  # If using git
source venv/bin/activate
pip install -r requirements.txt
systemctl restart scraper
```

## Total Time: ~30 minutes

## Monthly Cost: $12-24 (depending on droplet size)