# Deployment Instructions for Render.com

## Prerequisites
- GitHub account
- Render.com account (free tier works)
- Firecrawl API key

## Step-by-Step Deployment

### 1. Push Code to GitHub
```bash
# Create a new repository on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/intelliscrape-pro.git
git branch -M main
git push -u origin main
```

### 2. Deploy on Render

1. **Log in to Render.com**
   - Go to https://render.com
   - Sign in with GitHub

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `intelliscrape-pro` repository

3. **Configure Service**
   - **Name**: intelliscrape-pro
   - **Region**: Choose nearest to you
   - **Branch**: main
   - **Root Directory**: Leave empty
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

4. **Set Environment Variables**
   - Click "Advanced" → "Add Environment Variable"
   - Add required variables:
     - `FIRECRAWL_API_KEY`: Your Firecrawl API key
     - `GROQ_API_KEY`: Your Groq API key (optional)

5. **Choose Plan**
   - Select "Free" tier to start
   - Can upgrade later if needed

6. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Your app will be available at: `https://intelliscrape-pro.onrender.com`

## Post-Deployment

### Test Your Application
1. Visit your Render URL
2. Test scraping functionality with a small batch
3. Verify CSV export works

### Monitor Performance
- Check Render dashboard for:
  - Request logs
  - Error logs
  - Resource usage

### Custom Domain (Optional)
1. Go to Settings → Custom Domain
2. Add your domain
3. Update DNS records as instructed

## Troubleshooting

### Common Issues

**Build Fails**
- Check requirements.txt is complete
- Verify Python version in runtime.txt

**App Crashes**
- Check environment variables are set
- Review logs in Render dashboard

**Slow Performance**
- Free tier may sleep after inactivity
- Consider upgrading for better performance

## Security Notes
- Never commit API keys to GitHub
- Use Render's environment variables
- Enable HTTPS (automatic on Render)

## Next Steps
1. Set up auto-deploy from GitHub
2. Configure custom domain if needed
3. Monitor API usage and costs
4. Consider adding rate limiting