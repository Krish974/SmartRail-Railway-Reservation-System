# SmartRail Railway Reservation System — Cloud Deployment Guide

This guide describes how to deploy the SmartRail application to cloud hosting platforms (such as Render, Railway, Fly.io, Heroku, or an Ubuntu VPS).

---

## 1. Production Architecture Overview

- **Framework**: Flask (Python 3.10+)
- **WSGI Production Server**: Gunicorn
- **Application Factory / Entry Point**: `run:app` (located in `run.py`)
- **Static Assets & Frontend**: Served directly by Flask from the `frontend/` directory (routes: `/`, `/<page>`, `/<page>.html`).
- **REST APIs**: Blueprints mounted at `/api`, `/api/auth`, `/api/food`.
- **Health Check Endpoint**: `GET /api/health` (returns `{"success": true, "data": {"status": "HEALTHY", "version": "2.0.0"}}`).

---

## 2. Quick Reference Commands

| Step | Command |
| :--- | :--- |
| **Build Command** | `pip install -r requirements.txt` |
| **Production Start Command** | `gunicorn run:app` |
| **With Explicit Port / Binding** | `gunicorn --bind 0.0.0.0:$PORT run:app` |
| **Health Check URL** | `https://<your-domain>/api/health` |

---

## 3. Environment Variables Reference

Configure these environment variables in your cloud hosting provider's dashboard:

| Variable | Description | Production Recommended Value |
| :--- | :--- | :--- |
| `PORT` | Listening port injected by cloud provider | Automatically assigned (defaults to 5000) |
| `FLASK_ENV` | Environment mode | `production` |
| `FLASK_DEBUG` | Flask debug mode | `0` |
| `SECRET_KEY` | Secret key for session encryption & tokens | Secure 32+ character random string |
| `SESSION_COOKIE_SECURE` | Enforce HTTPS cookies | `1` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/dbname` |
| `DB_TYPE` | Active database type (`postgres`, `mysql`, `sqlite`, `auto`) | Automatically set to `postgres` when `DATABASE_URL` is present |
| `RAILRADAR_API_KEY` | RailRadar live train telemetry API key | Your private API key from [RailRadar](https://railradar.in) |
| `RAILRADAR_BASE_URL` | RailRadar API endpoint | `https://api.railradar.in` |
| `RAILRADAR_ROUTE_DELAY` | Polling delay between station route points | `1.0` |

> [!IMPORTANT]
> Never commit `.env` containing sensitive credentials to GitHub. Always set secrets through your hosting provider's environment variables dashboard.

---

## 4. Production Database Configuration (PostgreSQL)

SmartRail supports PostgreSQL natively via `psycopg2-binary` and connection pooling through `DATABASE_URL`.

### Database Initialization
To protect existing data, SmartRail does **not** automatically wipe or overwrite an existing production database upon startup.

When setting up a new PostgreSQL database (e.g. on Render, Railway, Supabase, or AWS RDS):
1. Create a PostgreSQL instance on your provider.
2. Copy the database connection URL and set it as `DATABASE_URL` in your web service's environment variables.
3. Apply the production schema using the provided `database/schema_postgres.sql`:
   ```bash
   psql "$DATABASE_URL" -f database/schema_postgres.sql
   ```

### Local Development Fallback
If `DATABASE_URL` is omitted and MySQL is not configured, the system automatically falls back to the embedded SQLite database at `database/railway_db.sqlite` without requiring any setup.

---

## 5. Platform Deployment Walkthroughs

### Option A: Render (Recommended)

1. **Create Web Service**:
   - Connect your GitHub repository: `https://github.com/Krish974/SmartRail-Railway-Reservation-System`
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn run:app`
2. **Attach Managed PostgreSQL**:
   - In Render Dashboard, click **New +** -> **PostgreSQL**.
   - Copy the **Internal Database URL** and add it as `DATABASE_URL` under your Web Service's **Environment** tab.
3. **Set Environment Variables**:
   - `SECRET_KEY`: `<generate-a-random-secret>`
   - `FLASK_ENV`: `production`
   - `FLASK_DEBUG`: `0`
   - `SESSION_COOKIE_SECURE`: `1`
   - `RAILRADAR_API_KEY`: `<your-railradar-key>`
4. **Deploy**:
   - Click **Deploy Latest Commit**.
   - Verify deployment by visiting `https://<your-service>.onrender.com/api/health`.

---

### Option B: Railway

1. In Railway, click **New Project** -> **Deploy from GitHub repo**.
2. Select `SmartRail-Railway-Reservation-System`.
3. Add a **PostgreSQL** service to the project. Railway automatically exposes `DATABASE_URL` to your app service.
4. Railway will automatically detect the root `Procfile` (`web: gunicorn run:app`).
5. Set `SECRET_KEY`, `RAILRADAR_API_KEY`, `FLASK_ENV=production`, `FLASK_DEBUG=0` under the Variables tab.

---

### Option C: Heroku

1. Create application:
   ```bash
   heroku create smartrail-app
   ```
2. Provision PostgreSQL:
   ```bash
   heroku addons:create heroku-postgresql:essential-0
   ```
3. Set environment variables:
   ```bash
   heroku config:set SECRET_KEY="<your-secret-key>" FLASK_ENV=production FLASK_DEBUG=0 RAILRADAR_API_KEY="<your-api-key>"
   ```
4. Push to deploy:
   ```bash
   git push heroku main
   ```

---

## 6. Pre-Flight Verification Checklist

- [x] Application factory in `run.py` exposed at module level (`app = create_app()`).
- [x] Gunicorn included in `requirements.txt` and `Procfile` configured.
- [x] Server binds dynamically to host `0.0.0.0` and `$PORT`.
- [x] Relative API routing in `frontend/js/main.js` adapts to any custom domain or port.
- [x] PostgreSQL support enabled via `DATABASE_URL` with SQLite development fallback preserved.
- [x] All secrets and API keys managed strictly via environment variables.
- [x] Full test suite verified (`pytest` and end-to-end booking verification).
