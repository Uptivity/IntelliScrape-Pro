# Docker Deployment Guide for Kieran

## Quick Setup for Digital Ocean

### Files Created:
- `Dockerfile` - Container build instructions
- `.dockerignore` - Files to exclude from container

### For Digital Ocean App Platform (Recommended):

1. **Connect GitHub Repository**
   - Go to Digital Ocean App Platform
   - Connect the FrontEndScraper repository
   - Select main/master branch

2. **App Configuration:**
   - **Name**: marketplace-scraper-pro
   - **Source**: GitHub repository
   - **Build Command**: Docker (auto-detected)
   - **Port**: 5000

3. **Environment Variables to Set:**
   ```
   FIRECRAWL_API_KEY=<user_will_provide>
   GROQ_API_KEY=<user_will_provide>
   FLASK_ENV=production
   ```

4. **Plan Selection:**
   - Start with Basic Plan ($5/month)
   - Can scale up based on usage

### Local Testing (if Docker is installed):
```bash
# Build container
docker build -t marketplace-scraper .

# Test locally
docker run -p 5000:5000 -e FIRECRAWL_API_KEY=test marketplace-scraper

# Visit http://localhost:5000
```

### Alternative: Traditional Droplet Deployment
If App Platform doesn't work, use the existing DIGITAL_OCEAN_DEPLOYMENT.md guide.

### Expected Result:
- App should be accessible at provided Digital Ocean URL
- All functionality should work identical to local development
- Auto-deploys when code is pushed to GitHub

### Troubleshooting:
- Check build logs in Digital Ocean dashboard
- Verify environment variables are set
- Ensure port 5000 is properly configured