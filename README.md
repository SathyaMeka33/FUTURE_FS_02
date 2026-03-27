# Mini CRM (Client Lead Management System)

Production-ready mini CRM built with Django, Django REST Framework, PostgreSQL (NeonDB-compatible), and plain HTML/CSS/JavaScript.

## Features

- Public contact form to capture leads
- Admin authentication (token-based)
- Full lead management CRUD for authenticated users
- Lead status workflow: `new`, `contacted`, `converted`
- Inline notes update from dashboard
- Search by name/email
- Filter by status/source
- Ordering by created date
- Pagination (10 leads per page)
- Dashboard analytics:
  - Total leads
  - New leads
  - Contacted leads
  - Converted leads
  - Conversion rate

## Tech Stack

- Backend: Django 5, Django REST Framework, django-filter
- Auth: DRF Token Authentication
- Database: PostgreSQL (NeonDB-ready via SSL)
- Frontend: HTML, CSS, JavaScript (Fetch API)

## Folder Structure

```text
backend/
  .env.example
  manage.py
  requirements.txt
  crm_project/
    __init__.py
    asgi.py
    settings.py
    urls.py
    wsgi.py
  leads/
    __init__.py
    admin.py
    apps.py
    models.py
    permissions.py
    serializers.py
    views.py
    migrations/
      __init__.py
      0001_initial.py
frontend/
  index.html
  login.html
  dashboard.html
  style.css
  script.js
README.md
ACTION_LOG.txt
```

## Setup Instructions

### 1. Create and activate virtual environment

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure NeonDB/PostgreSQL

- Copy `backend/.env.example` to `backend/.env`
- Fill values:
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
  - `DB_PORT`
  - `DB_SSLMODE=require`

### 4. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create admin user

```bash
python manage.py createsuperuser
```

### 6. Start backend server

```bash
python manage.py runserver
```

### 7. Open frontend pages

Open these files using a static server (recommended) or directly in browser:
- `frontend/index.html`
- `frontend/login.html`
- `frontend/dashboard.html`

If serving frontend from a custom origin/port, add it to `CORS_ALLOWED_ORIGINS`.

## API Endpoints

### Auth

- `POST /api/auth/login/`
  - body: `{"username":"admin","password":"..."}`
  - returns auth token
- `POST /api/auth/logout/`
  - token required

### Leads

- `POST /api/leads/` (public)
- `GET /api/leads/` (auth required)
- `GET /api/leads/{id}/` (auth required)
- `PATCH /api/leads/{id}/` (auth required)
- `PUT /api/leads/{id}/` (auth required)
- `DELETE /api/leads/{id}/` (auth required)
- `GET /api/leads/analytics/` (auth required)

### Query Parameters

- Search: `?search=john`
- Filter: `?status=new&source=website`
- Ordering: `?ordering=-created_at`
- Pagination: `?page=2`

## Validation and Error Handling

- Required fields validated on frontend and backend
- API-level serializer validation for clean data
- Graceful error messages displayed in UI

## Screenshots

- Contact Form: _add screenshot here_
- Admin Login: _add screenshot here_
- Dashboard: _add screenshot here_

## Production Notes

- Set `DEBUG=False` in production
- Use strong `SECRET_KEY`
- Restrict `ALLOWED_HOSTS`
- Serve behind HTTPS
- Store secrets in environment variables only
