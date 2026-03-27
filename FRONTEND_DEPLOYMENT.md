# Frontend Deployment to Render

## What's Configured

✅ **script.js** - Automatically detects environment:
- Running on `localhost/127.0.0.1` → Uses local backend (`http://127.0.0.1:8000/api`)
- Running on production domain → Uses Render backend (`https://leadflow-hsyp.onrender.com/api`)

✅ **render.yaml** - Includes static site service for frontend:
```yaml
- type: static_site
  name: crm-frontend
  rootDir: frontend
  buildCommand: ""
  staticPublishPath: ./
```

## Deployment Steps

### 1. Deploy Frontend to Render

**Option A: Using `render.yaml` (Recommended)**

Since you have a backend service already deployed, you can now deploy the frontend through the same render.yaml:

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"** or **"Static Site"**
3. Connect your GitHub repository: `https://github.com/SathyaMeka33/FUTURE_FS_02`
4. Select **"Static Site"** as the service type
5. Set the following:
   - **Name:** `crm-frontend` (or any name)
   - **Root Directory:** `frontend`
   - **Build Command:** (leave empty - no build needed)
   - **Publish Directory:** `./` (current directory)
6. Click **"Deploy"**

**Option B: Manual GitHub Repo setup**

If Render doesn't auto-detect from render.yaml, manually create a Static Site:
1. GitHub repo URL: `https://github.com/SathyaMeka33/FUTURE_FS_02`
2. Branch: `main`
3. Root Directory: `frontend`
4. Publish Directory: `./`

### 2. Get Frontend URL

After deployment, Render will assign a URL like:
```
https://crm-frontend-xxxx.onrender.com
```

Save this URL for the next step.

### 3. Update Backend CORS Settings

Once frontend is deployed, update the backend service environment variables:

1. Go to Render Dashboard → Your backend service (`crm-backend`)
2. Go to **Settings** → **Environment**
3. Update or add these variables:

   **CORS_ALLOWED_ORIGINS:**
   ```
   https://crm-frontend-xxxx.onrender.com
   ```

   **CSRF_TRUSTED_ORIGINS:**
   ```
   https://crm-frontend-xxxx.onrender.com
   ```

4. Click **"Save Changes"** (this will automatically redeploy the backend)

### 4. Test the Full Deployment

1. Visit your frontend URL: `https://crm-frontend-xxxx.onrender.com/dashboard.html`
2. Try submitting a lead through the form
3. Login to admin dashboard with your credentials
4. Verify all API operations work

## Troubleshooting

### CORS Error (No 'Access-Control-Allow-Origin' header)

**Cause:** Backend's CORS_ALLOWED_ORIGINS not updated with frontend URL

**Fix:** 
1. Update CORS_ALLOWED_ORIGINS in backend environment variables (see Step 3 above)
2. Wait for backend to redeploy (automatic after saving changes)
3. Refresh frontend page

### API 401 Unauthorized

**Cause:** Token not sent or token expired

**Fix:** 
1. Open DevTools Console
2. Run: `localStorage.removeItem('crm_token')`
3. Reload page and login again

### Frontend Shows "Cannot reach backend"

**Cause:** Frontend using wrong API URL

**Fix:**
1. Open DevTools Console
2. Check current API URL: `localStorage.getItem('crm_api_base')`
3. If wrong, set correct one: `localStorage.setItem('crm_api_base', 'https://leadflow-hsyp.onrender.com/api')`
4. Reload page

## Local Development

To continue developing locally:

1. **Frontend:** Run in VS Code with Live Server or HTTP server
2. **Backend:** Start Django server: `python manage.py runserver 127.0.0.1:8000`
3. Frontend will auto-detect and use localhost backend

## Architecture After Deployment

```
┌─────────────────────────────────────────┐
│          Your Browser                   │
└────────────────┬────────────────────────┘
                 │
      ┌──────────┴──────────┐
      │                     │
      ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ Frontend (Static)│  │ Backend (Python) │
│ on Render        │  │ on Render        │
│ (HTML/CSS/JS)    │  │ (REST API)       │
│                  │  │                  │
│ API calls to ──────→ /api/             │
│ backend via CORS │  │                  │
└──────────────────┘  └────────┬─────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Neon Database    │
                        │ (PostgreSQL)     │
                        └──────────────────┘
```

## Files Modified

- `frontend/script.js` - Auto-detect API URL based on environment
- `render.yaml` - Added static site service for frontend
- `ACTION_LOG.txt` - Audit trail

All changes pushed to GitHub `main` branch.
