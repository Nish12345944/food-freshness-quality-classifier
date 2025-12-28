# 🚀 Deployment Guide - Render

## Prerequisites
- GitHub account
- Render account (free tier available at https://render.com)
- Git installed on your local machine

## Step-by-Step Deployment Instructions

### 1. Prepare Your Repository

**Push your code to GitHub:**

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial commit - Food Freshness Classifier"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/food-freshness-classifier.git

# Push to GitHub
git push -u origin main
```

### 2. Create Render Account

1. Go to https://render.com
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

### 3. Deploy on Render

**Create a New Web Service:**

1. Click **"New +"** button in Render dashboard
2. Select **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

   **Basic Settings:**
   - **Name:** `food-freshness-classifier` (or your preferred name)
   - **Region:** Choose closest to your location
   - **Branch:** `main`
   - **Root Directory:** Leave blank
   - **Runtime:** `Python 3`
   - **Build Command:** `./build.sh`
   - **Start Command:** `gunicorn app:app`

   **Instance Type:**
   - Select **Free** tier (or paid if needed)

5. Click **"Advanced"** and add Environment Variables:

   ```
   SECRET_KEY = your-secret-key-here-make-it-random
   PYTHON_VERSION = 3.11.0
   ```

6. Click **"Create Web Service"**

### 4. Wait for Deployment

- Render will automatically:
  - Install dependencies from `requirements.txt`
  - Run `build.sh` to set up directories and database
  - Start the application with gunicorn
  
- Deployment typically takes 5-10 minutes
- Monitor the logs in real-time on Render dashboard

### 5. Access Your Application

Once deployed, Render will provide a URL like:
```
https://food-freshness-classifier.onrender.com
```

**Default Login Credentials:**
- Username: `admin`
- Password: `password`

⚠️ **IMPORTANT:** Change the default password immediately after first login!

## 🔧 Configuration Options

### Environment Variables (Optional)

Add these in Render dashboard under "Environment":

```bash
# Required
SECRET_KEY=your-super-secret-random-key-here

# Optional - Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=your-email@gmail.com
SENDER_PASSWORD=your-app-password

# Optional - Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname
```

### Using PostgreSQL (Recommended for Production)

1. In Render dashboard, create a **PostgreSQL** database
2. Copy the **Internal Database URL**
3. Add it as `DATABASE_URL` environment variable
4. Update `requirements.txt` to include:
   ```
   psycopg2-binary==2.9.9
   ```

## 📝 Post-Deployment Steps

### 1. Test the Application
- Visit your Render URL
- Test login functionality
- Upload a test image
- Verify all features work

### 2. Custom Domain (Optional)
1. Go to your web service settings
2. Click "Custom Domain"
3. Add your domain and follow DNS instructions

### 3. Enable Auto-Deploy
- Render automatically deploys on every push to `main` branch
- Disable in settings if you want manual deployments

## 🐛 Troubleshooting

### Build Fails
- Check logs in Render dashboard
- Verify `requirements.txt` has correct package versions
- Ensure `build.sh` has execute permissions

### Application Crashes
- Check application logs
- Verify environment variables are set
- Ensure database is initialized

### Camera Feature Not Working
- Webcam capture won't work on server (expected)
- Feature will be disabled automatically
- Works only on local development

### Upload Issues
- Render free tier has limited disk space
- Consider using cloud storage (AWS S3, Cloudinary) for production
- Implement file cleanup for old uploads

## 🔄 Updating Your Application

```bash
# Make changes locally
git add .
git commit -m "Your update message"
git push origin main

# Render will automatically redeploy
```

## 💰 Cost Considerations

**Free Tier Limitations:**
- Service spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds
- 750 hours/month free

**Paid Tier Benefits ($7/month):**
- Always-on service
- No cold starts
- More resources
- Better performance

## 📊 Monitoring

- View logs in Render dashboard
- Set up email alerts for failures
- Monitor resource usage

## 🔒 Security Best Practices

1. **Change default credentials immediately**
2. **Use strong SECRET_KEY** (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)
3. **Enable HTTPS** (automatic on Render)
4. **Don't commit sensitive data** to GitHub
5. **Use environment variables** for all secrets

## 📞 Support

- Render Documentation: https://render.com/docs
- Render Community: https://community.render.com
- GitHub Issues: Create an issue in your repository

---

✅ **Your Food Freshness Classifier is now live!**

Share your deployment URL and start classifying food freshness! 🍎🥗
