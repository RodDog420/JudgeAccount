# DEPLOYMENT INSTRUCTIONS FOR RENDER

## Prerequisites
1. GitHub account (to host your code)
2. Render account (free tier is fine): https://render.com
3. Your domain registrar access (to point judgeaccount.com to Render)

## Step 1: Prepare Your Code

### Files to add to your project root:
✅ requirements.txt (updated with gunicorn and psycopg2-binary)
✅ render.yaml (deployment configuration)
✅ build.sh (build script for migrations)
✅ .gitignore (prevents sensitive files from being committed)

### Make build.sh executable:
```bash
chmod +x build.sh
```

## Step 2: Push to GitHub

### If you don't have a Git repository yet:
```bash
# In your project root directory
git init
git add .
git commit -m "Initial commit for deployment"

# Create a new repository on GitHub (https://github.com/new)
# Name it "judgeaccount" or similar
# Then connect and push:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### If you already have a Git repository:
```bash
git add .
git commit -m "Add Render deployment files"
git push
```

## Step 3: Deploy on Render

### Option A: Use render.yaml (Recommended - Automated)
1. Go to https://render.com/dashboard
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Render will automatically detect render.yaml
5. Click "Apply" - Render will create:
   - Web Service (your Flask app)
   - PostgreSQL database (free tier)
   - Automatically link them together

### Option B: Manual Setup
1. Create PostgreSQL database first:
   - Click "New +" → "PostgreSQL"
   - Name: judgeaccount-db
   - Database: judgeaccount
   - User: judgeaccount
   - Click "Create Database"
   - Copy the "Internal Database URL" (you'll need this)

2. Create Web Service:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Name: judgeaccount
   - Runtime: Python 3
   - Build Command: `./build.sh`
   - Start Command: `gunicorn judge_review:app`
   - Instance Type: Free
   
3. Add Environment Variables:
   - Click "Environment" tab
   - Add: 
     * `SECRET_KEY` = (click "Generate" for random secure key)
     * `DATABASE_URL` = (paste the Internal Database URL from step 1)
   - Save Changes

## Step 4: Wait for Deployment
- Render will build and deploy (takes 5-10 minutes first time)
- Watch the logs for any errors
- Once complete, you'll get a URL like: `https://judgeaccount.onrender.com`

## Step 5: Set Up Custom Domain (judgeaccount.com)

### In Render:
1. Go to your web service settings
2. Click "Custom Domain"
3. Add "judgeaccount.com" and "www.judgeaccount.com"
4. Render will show you DNS records to add

### In Your Domain Registrar (GoDaddy, Namecheap, etc.):
1. Go to DNS settings for judgeaccount.com
2. Add the CNAME records Render provides:
   - Type: CNAME
   - Name: www
   - Value: judgeaccount.onrender.com (or whatever Render provides)
   
   - Type: A
   - Name: @
   - Value: (IP address Render provides)

3. Save DNS changes (can take 15 minutes to 48 hours to propagate)

## Step 6: Initialize Database

### One-time setup after first deployment:
Your migrations should run automatically via build.sh, but if you need to manually initialize:

1. Go to Render dashboard → Your web service
2. Click "Shell" tab
3. Run:
```bash
flask db upgrade
```

## Step 7: Verify Deployment
1. Visit your Render URL: https://judgeaccount.onrender.com
2. Test key features:
   - Home page loads
   - Can register/login
   - Can submit review/media
   - All pages render correctly

## Step 8: Complete Stripe Setup
Now that your site is live:
1. Go back to Stripe setup
2. Enter: https://judgeaccount.com as your business website
3. Complete verification
4. Get payment links
5. Update support.html with real Stripe links

## Troubleshooting

### Build fails:
- Check Render logs for specific error
- Common issues:
  * Missing dependency in requirements.txt
  * build.sh not executable: run `chmod +x build.sh` locally and commit
  * Database migration error: check migrations folder

### App won't start:
- Check Start Command is exactly: `gunicorn judge_review:app`
- Verify environment variables are set correctly
- Check that DATABASE_URL is from PostgreSQL (not SQLite)

### Database errors:
- Ensure DATABASE_URL environment variable is set
- Verify PostgreSQL database is created and running
- Check migrations have run: `flask db upgrade`

### Static files (CSS/JS) not loading:
- Flask should serve static files automatically
- Verify your static folder structure is correct
- Check browser console for 404 errors

## Important Notes

1. **Free Tier Limitations:**
   - Render free tier spins down after 15 min of inactivity
   - First request after spin-down takes 30-60 seconds
   - Upgrade to paid tier ($7/mo) for always-on service

2. **Environment Variables:**
   - NEVER commit .env to Git (it's in .gitignore)
   - Set all environment variables in Render dashboard
   - SECRET_KEY should be different from your local dev key

3. **Database Backups:**
   - Free PostgreSQL has no automatic backups
   - Upgrade to paid tier for daily backups
   - Or manually backup: `pg_dump` command

4. **Monitoring:**
   - Watch Render logs for errors
   - Set up error tracking (Sentry, etc.) for production
   - Monitor database size (free tier has 1GB limit)

## After Successful Deployment

Update your local .env to test against production database (optional):
```
# Don't do this unless you need to test production data locally
DATABASE_URL=<production-postgres-url>
SECRET_KEY=<production-secret-key>
```

Better approach: Keep development and production separate!