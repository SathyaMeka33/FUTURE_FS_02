# Render Deployment Guide

## Prerequisites
- GitHub account with repository access
- Render account (render.com)
- Neon PostgreSQL database URL

## Backend Deployment (Render)

### Step 1: Push Code to GitHub

```bash
git config user.email "your-email@example.com"
git config user.name "Your Name"
git add .
git commit -m "Initial CRM project commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### Step 2: Create Render Web Service

1. Go to https://dashboard.render.com
2. Click **New +** → **Web Service**
3. Select your GitHub repository
4. Configure:
   - **Name:** `crm-backend`
   - **Region:** Choose closest to your users
   - **Branch:** `main`
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt && python manage.py migrate`
   - **Start Command:** `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT`

### Step 3: Set Environment Variables

In Render dashboard, add these under **Environment**:

```
SECRET_KEY=<generate-randomly-or-use-django-secret-key-generator>
DEBUG=False
ALLOWED_HOSTS=<your-render-domain>.onrender.com
DATABASE_URL=postgresql://neondb_owner:XXX@ep-calm-shadow-a1irvadp-pooler.ap-southeast-1.aws.neon.tech/CRM?sslmode=require&channel_binding=require
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://<your-vercel-frontend-domain>
```

### Step 4: Deploy

Click **Create Web Service**. Render will:
- Clone your repo
- Install dependencies
- Run migrations
- Start the server

**Check logs** for any errors. Your backend URL: `https://<service-name>.onrender.com`

---

## Frontend Deployment (Vercel)

### Step 1: Deploy Frontend

1. Go to https://vercel.com
2. Click **Add New** → **Project**
3. Import your GitHub repository
4. Configure:
   - **Framework:** React
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `out`

### Step 2: Set Environment Variable

Add in **Environment Variables**:
```
REACT_APP_API_BASE_URL=https://<your-render-backend>.onrender.com
```

### Step 3: Deploy

Click **Deploy**. Vercel will handle the rest.

---

## Testing After Deployment

### Test 1: Lead Submission (Public)
```bash
curl -X POST https://<your-render-backend>.onrender.com/api/leads/ \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "phone_number": "1234567890",
    "service_interested": "web_development",
    "source": "google",
    "notes": "Test lead"
  }'
```

### Test 2: Get Auth Token
```bash
curl -X POST https://<your-render-backend>.onrender.com/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-password"
  }'
```

### Test 3: Admin Dashboard
Visit `https://<your-vercel-frontend>.vercel.app` and:
1. Click "Go to Admin"
2. Enter credentials
3. Verify leads appear
4. Test filtering, sorting, bookmarking

---

## Troubleshooting

**Backend fails to start:**
- Check logs in Render dashboard
- Verify `DATABASE_URL` is correct
- Ensure migrations ran successfully

**Frontend can't connect to backend:**
- Verify `REACT_APP_API_BASE_URL` is set
- Check CORS settings in `Django core/settings.py`
- Ensure backend is running

**Database connection errors:**
- Test Neon connection string locally first
- Verify SSL mode is `require`
- Check Neon dashboard for active connections

---

## Custom Domain (Optional)

1. In Render dashboard, go to **Settings** → **Custom Domain**
2. Add your domain (e.g., `crm.yourdomain.com`)
3. Update DNS records as instructed
4. SSL certificate auto-generates in ~30 minutes

---

## Monitoring & Updates

- **Logs:** View in Render dashboard under **Logs**
- **Auto-deploy:** Set up in **Settings** → **Auto Deploy**
- **Environment changes:** Re-deploy via **Manual Deploy** button

