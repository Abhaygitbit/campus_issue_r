# 🚀 Deployment Guide - CIRS on Render

This guide walks you through deploying the Campus Issues Reporting System (CIRS) to Render.com for free hosting.

---

## Option A: Quick Deploy (SQLite - Development Only)

If you want to test quickly with SQLite:

1. Push to GitHub
2. Create a Web Service on Render
3. Set environment variables:
   ```
   RENDER=true
   USE_SQLITE=true
   JWT_SECRET=your-random-secret-key
   ```
4. Deploy!

⚠️ **Note:** SQLite is fine for testing but not recommended for production (single user at a time).

---

## Option B: Production Deploy (PostgreSQL - Recommended)

### Prerequisites
- GitHub account with your repo pushed
- Render.com account (free tier available)

### Step 1: Create PostgreSQL Database on Render

1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click **"New +"** → **"PostgreSQL"**
3. Fill in:
   - **Name:** `cirs-db`
   - **Database:** `cirs`
   - **User:** `cirs_user`
   - Region: Choose nearest to you
4. Click **"Create Database"**
5. Wait for creation (5-10 min)
6. **Copy the connection string** from the database page

### Step 2: Deploy Flask Backend

1. Go to [render.com/dashboard](https://render.com/dashboard)
2. Click **"New +"** → **"Web Service"**
3. Select your GitHub repository (CIRS)
4. Fill in:
   - **Name:** `cirs-api`
   - **Runtime:** Python 3.10
   - **Build Command:** 
     ```
     pip install -r requirements.txt
     ```
   - **Start Command:**
     ```
     gunicorn -w 4 -b 0.0.0.0:$PORT backend.app:app
     ```
5. Click **"Advanced"** and add **Environment Variables:**

   | Variable | Value |
   |----------|-------|
   | `RENDER` | `true` |
   | `RENDER_EXTERNAL_URL` | `https://cirs-api.onrender.com` (or your actual URL after deploy) |
   | `USE_SQLITE` | `false` |
   | `DB_HOST` | From PostgreSQL connection string |
   | `DB_NAME` | `cirs` |
   | `DB_USER` | `cirs_user` |
   | `DB_PASSWORD` | From PostgreSQL connection string |
   | `DB_PORT` | `5432` |
   | `JWT_SECRET` | Generate a random string: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

6. Click **"Create Web Service"**
7. Wait for deployment (2-3 minutes)

### Step 3: Verify Deployment

- Check Render dashboard for the deployed URL
- Visit `https://your-app-name.onrender.com` in browser
- Should see the CIRS login page

---

## Environment Variables Explained

```bash
# Render Detection
RENDER=true                                    # Tells app it's running on Render
RENDER_EXTERNAL_URL=https://your-url.onrender.com  # Your deployed URL

# Database
USE_SQLITE=false                              # Use PostgreSQL, not SQLite
DB_HOST=your-db-host.c.render.com            # From Render PostgreSQL
DB_NAME=cirs                                  # Database name
DB_USER=cirs_user                             # Database user
DB_PASSWORD=your_secure_password              # Database password
DB_PORT=5432                                  # PostgreSQL port

# Security
JWT_SECRET=random-secret-key-min-32-chars    # Used for JWT token signing

# Email (Optional)
SMTP_USER=your-email@gmail.com                # Gmail or SMTP server
SMTP_PASS=your-app-specific-password          # App password (not your Gmail password)
SMTP_HOST=smtp.gmail.com                      # Gmail SMTP server
SMTP_PORT=587                                 # Gmail SMTP port
EMAIL_FROM=your-email@gmail.com               # From address
EMAIL_VERIFY_ENABLED=false                    # Email verification for new users
```

---

## Troubleshooting

### "Build failed"
- Check build logs in Render dashboard
- Verify `requirements.txt` exists
- Ensure Python 3.10+ runtime selected

### "App keeps crashing"
- Check logs: Render Dashboard → Logs
- Verify environment variables are set
- Check PostgreSQL connection string is correct

### "Database connection refused"
- Make sure PostgreSQL service is available (not deleted)
- Check DB_HOST, DB_USER, DB_PASSWORD are correct
- Ensure USE_SQLITE=false

### "502 Bad Gateway"
- App might still be starting (wait 1-2 minutes)
- Check if gunicorn command is running: `gunicorn -w 4 -b 0.0.0.0:$PORT backend.app:app`

---

## Performance Tips

- Render free tier: auto-spins down after 15 min inactivity (cold start)
- For always-on: upgrade to paid tier
- Use PostgreSQL for better performance than SQLite
- Database backups: configure in Render dashboard

---

## First Time Setup After Deploy

Once deployed, you'll need to:

1. Create an admin account
2. Create departments/categories
3. Configure email (if enabled)

Default admin credentials are created automatically:
- **Email:** `admin@cdgi.edu.in`
- **Password:** `admin123`

⚠️ **Change this immediately after first login!**

---

## Rollback & Updates

To update the app:
1. Make changes locally
2. Commit and push to GitHub
3. Render automatically redeploys
4. Check logs for any errors

To rollback:
- Go to Render Dashboard → Logs
- Find previous deployment
- Click "Redeploy" on that version

---

## Additional Resources

- [Render Documentation](https://docs.render.com)
- [PostgreSQL Free Tier](https://render.com/docs/databases)
- [Flask Deployment](https://flask.palletsprojects.com/en/2.3.x/deploying/)

---

Need help? Check the main [README.md](./README.md) or create a GitHub issue.
