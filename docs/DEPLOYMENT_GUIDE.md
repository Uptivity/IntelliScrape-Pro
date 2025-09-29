# 🌐 Complete Web Deployment Guide
## From Local Flask App to Live Website

*Your portable reference for deploying the FrontEnd Scraper to production*

---

## 📋 **What You Need (Checklist)**

- [ ] DigitalOcean account (or similar VPS provider)
- [ ] Domain name (optional but recommended) - $10-15/year
- [ ] Credit card for server costs (~$6/month)
- [ ] SSH client (built into Windows/Mac/Linux)
- [ ] Your Flask app files ready

---

## 🎯 **Understanding the Big Picture**

### **Current Setup (Local)**
```
Your Computer
├── Flask app runs on localhost:5000
├── Only you can access it
├── Stops when you close laptop
└── Uses browser localStorage
```

### **Target Setup (Production)**
```
Internet → Domain Name → DigitalOcean Server → Your Flask App
         (yoursite.com)   (142.93.45.123)    (port 5000)
```

### **What Each Component Does:**
- **VPS (Virtual Private Server)**: Your dedicated computer in the cloud
- **SSH**: Remote control of your server (like remote desktop but text-based)
- **Nginx**: Professional web server (handles multiple users efficiently)
- **PM2**: Keeps your app running 24/7 (auto-restarts if crashes)
- **Domain**: Pretty name instead of IP address
- **SSL**: HTTPS security (padlock icon)

---

## 🚀 **Step-by-Step Deployment**

### **PHASE 1: Create Your Server**

#### **1.1 Create DigitalOcean Account**
1. Go to **digitalocean.com**
2. Sign up with email/password
3. Verify email address
4. Add credit card (they often give $100 free credit)

#### **1.2 Create a Droplet (Server)**
1. Click **"Create"** → **"Droplet"**
2. **Image**: Choose **Ubuntu 22.04 LTS**
3. **Plan**: Select **Basic** → **$6/month** (1GB RAM, 25GB SSD)
4. **Region**: Choose closest to your users
5. **Authentication**:
   - **Recommended**: SSH Key (more secure)
   - **Easy**: Password (write it down!)
6. **Hostname**: `flask-scraper-app`
7. Click **"Create Droplet"**

**⏰ Wait 2-3 minutes for server creation**

#### **1.3 Get Server Details**
- **IP Address**: `142.93.45.123` (example - yours will be different)
- **Username**: `root`
- **Password**: What you set (if using password auth)

---

### **PHASE 2: Connect to Your Server**

#### **2.1 Open Command Line**
- **Windows**: PowerShell or Command Prompt
- **Mac**: Terminal
- **Linux**: Terminal

#### **2.2 Connect via SSH**
```bash
ssh root@YOUR_SERVER_IP
# Example: ssh root@142.93.45.123
```

**First Connection:**
- Type `yes` when asked about authenticity
- Enter password when prompted
- You should see: `root@flask-scraper-app:~#`

**🎉 Success! You're now controlling your server remotely**

---

### **PHASE 3: Prepare Your Server**

#### **3.1 Update System**
```bash
apt update && apt upgrade -y
```
*⏰ Takes 2-5 minutes*

#### **3.2 Install Required Software**
```bash
# Install Python and pip
apt install python3 python3-pip python3-venv -y

# Install web server
apt install nginx -y

# Install Git (for code management)
apt install git -y

# Install Node.js and PM2 (process manager)
apt install nodejs npm -y
npm install -g pm2
```
*⏰ Takes 3-7 minutes*

---

### **PHASE 4: Upload Your Code**

#### **4.1 Create App Directory**
```bash
mkdir /var/www/flask-scraper
cd /var/www/flask-scraper
```

#### **4.2 Upload Your Code (Choose One Method)**

**Method A: GitHub (Recommended)**
```bash
# If your code is on GitHub
git clone https://github.com/yourusername/your-repo.git .
```

**Method B: Manual File Transfer**
```bash
# From your local computer (new terminal/command prompt)
scp -r C:\claude\FrontEndScraper\* root@YOUR_SERVER_IP:/var/www/flask-scraper/
```

**Method C: SFTP Client**
1. Download **FileZilla** or **WinSCP**
2. Connect using server IP and credentials
3. Drag and drop files

---

### **PHASE 5: Configure Your App**

#### **5.1 Set Up Python Environment**
```bash
cd /var/www/flask-scraper
python3 -m venv venv
source venv/bin/activate
```

#### **5.2 Install Dependencies**
```bash
pip install flask requests beautifulsoup4 firecrawl-py
# Add any other packages your app uses
```

#### **5.3 Test Your App**
```bash
python3 app.py
```

**Expected Output:**
```
* Running on http://127.0.0.1:5000
* Debug mode: on
```

**Test it:** Visit `http://YOUR_SERVER_IP:5000` in browser
**Stop it:** Press `Ctrl+C`

---

### **PHASE 6: Production Web Server**

#### **6.1 Install Production Server**
```bash
pip install gunicorn
```

#### **6.2 Create Gunicorn Config**
```bash
nano /var/www/flask-scraper/gunicorn.conf.py
```

**Add this content:**
```python
bind = "127.0.0.1:5000"
workers = 2
timeout = 120
max_requests = 1000
keepalive = 2
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

#### **6.3 Configure Nginx**
```bash
nano /etc/nginx/sites-available/flask-scraper
```

**Add this content:**
```nginx
server {
    listen 80;
    server_name YOUR_SERVER_IP;  # Replace with your IP or domain

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/flask-scraper/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

#### **6.4 Enable Nginx Site**
```bash
ln -s /etc/nginx/sites-available/flask-scraper /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default
nginx -t  # Test configuration
systemctl reload nginx
```

---

### **PHASE 7: Auto-Start Your App**

#### **7.1 Create PM2 Config**
```bash
nano /var/www/flask-scraper/ecosystem.config.js
```

**Add this content:**
```javascript
module.exports = {
  apps: [{
    name: 'flask-scraper',
    script: '/var/www/flask-scraper/venv/bin/gunicorn',
    args: '-c gunicorn.conf.py app:app',
    cwd: '/var/www/flask-scraper',
    env: {
      PYTHONPATH: '/var/www/flask-scraper'
    },
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G'
  }]
}
```

**Save and exit:** `Ctrl+X`, then `Y`, then `Enter`

#### **7.2 Start Your App**
```bash
cd /var/www/flask-scraper
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Follow the instructions this gives you
```

**🎉 Your app is now live!** Visit `http://YOUR_SERVER_IP`

---

### **PHASE 8: Domain Name (Optional)**

#### **8.1 Buy Domain**
1. Go to **Namecheap**, **GoDaddy**, or **Cloudflare**
2. Search for available domain: `myscrapertool.com`
3. Purchase domain (~$10-15/year)

#### **8.2 Point Domain to Server**
In your domain registrar's DNS settings:

**A Record:**
- **Name**: `@` (root domain)
- **Value**: `YOUR_SERVER_IP`
- **TTL**: `300`

**CNAME Record:**
- **Name**: `www`
- **Value**: `myscrapertool.com`
- **TTL**: `300`

#### **8.3 Update Nginx**
```bash
nano /etc/nginx/sites-available/flask-scraper
```

**Change the server_name line:**
```nginx
server_name myscrapertool.com www.myscrapertool.com;
```

```bash
systemctl reload nginx
```

**⏰ DNS propagation takes 1-24 hours**

---

### **PHASE 9: HTTPS Security (Optional)**

#### **9.1 Install Certbot**
```bash
apt install certbot python3-certbot-nginx -y
```

#### **9.2 Get Free SSL Certificate**
```bash
certbot --nginx -d myscrapertool.com -d www.myscrapertool.com
```

**Follow prompts:**
- Enter email
- Accept terms
- Choose redirect option (recommended)

**🔒 Your site now has HTTPS!**

---

## 🛠️ **Daily Management Commands**

### **Check App Status**
```bash
pm2 status
pm2 logs flask-scraper
```

### **Restart App**
```bash
pm2 restart flask-scraper
```

### **Update Your Code**
```bash
cd /var/www/flask-scraper
git pull  # If using Git
pm2 restart flask-scraper
```

### **Check Server Resources**
```bash
htop  # Press 'q' to exit
df -h  # Disk space
free -h  # Memory usage
```

### **Check Web Server**
```bash
systemctl status nginx
systemctl restart nginx  # If needed
```

---

## 🚨 **Troubleshooting**

### **App Won't Start**
```bash
cd /var/www/flask-scraper
source venv/bin/activate
python3 app.py  # Check for errors
```

### **Can't Access Website**
```bash
# Check if app is running
pm2 status

# Check nginx
systemctl status nginx
nginx -t  # Test config

# Check firewall
ufw status
```

### **Domain Not Working**
1. Wait 24 hours for DNS propagation
2. Check DNS: `nslookup myscrapertool.com`
3. Verify A record points to correct IP

### **SSL Certificate Issues**
```bash
certbot renew --dry-run
certbot certificates
```

---

## 💰 **Monthly Costs**

| Item | Cost | Purpose |
|------|------|---------|
| DigitalOcean Droplet | $6/month | Server hosting |
| Domain Name | $1/month | Pretty URL |
| SSL Certificate | Free | Security (Let's Encrypt) |
| **Total** | **~$7/month** | Professional website |

---

## 🔄 **Architecture Overview**

```
User → Domain → Nginx → Gunicorn → Flask App
     ↓
   HTTPS    Load    Production   Your
 Security  Balancer   Server    Code
```

**Data Flow:**
1. User visits `myscrapertool.com`
2. DNS resolves to your server IP
3. Nginx receives the request
4. Nginx forwards to Gunicorn
5. Gunicorn runs your Flask app
6. Response travels back to user

---

## 📝 **Quick Reference**

### **Essential File Locations**
- **App Code**: `/var/www/flask-scraper/`
- **Nginx Config**: `/etc/nginx/sites-available/flask-scraper`
- **PM2 Config**: `/var/www/flask-scraper/ecosystem.config.js`
- **Logs**: `pm2 logs flask-scraper`

### **Key Commands**
```bash
# Connect to server
ssh root@YOUR_SERVER_IP

# Restart everything
pm2 restart flask-scraper
systemctl reload nginx

# Update code and restart
cd /var/www/flask-scraper && git pull && pm2 restart flask-scraper

# Check status
pm2 status && systemctl status nginx
```

### **Emergency Contacts**
- **DigitalOcean Support**: Available 24/7 via ticket
- **Domain Registrar**: Check their support page
- **This Guide**: Keep handy for reference!

---

## 🎯 **Success Checklist**

- [ ] Server created and accessible via SSH
- [ ] Code uploaded and dependencies installed
- [ ] App starts without errors locally
- [ ] Nginx configured and running
- [ ] PM2 managing your app
- [ ] Website accessible via IP address
- [ ] Domain configured (if purchased)
- [ ] HTTPS working (if configured)
- [ ] Auto-restart on server reboot enabled

---

## 🔗 **Useful Links**

- [DigitalOcean Docs](https://docs.digitalocean.com)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/)
- [Let's Encrypt](https://letsencrypt.org/)

---

**💡 Pro Tips:**
- Always test locally before deploying
- Keep backups of your code
- Monitor server resources regularly
- Update system packages monthly
- Set up monitoring/alerts for production

**🎉 Congratulations! Your Flask scraper is now a professional web application!**