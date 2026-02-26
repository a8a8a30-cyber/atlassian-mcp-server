# Car Rental Admin MVP (Low Cost)

This repository contains a lightweight internal car rental management system
designed for fast deployment and very low operating cost.

## Stack

- Python 3.12
- Flask
- Flask-SQLAlchemy
- SQLite (default local database)
- Bootstrap 5 (CDN)

## Included MVP Features

- Arabic RTL web interface (mobile/tablet friendly)
- Branch management
- Fleet management (vehicles, status, daily rates, GPS device ID)
- Reservation management with overlap validation
- Contract lifecycle (start/close contract)
- GPS point logging (manual input for now)
- Dashboard with operational counters and monthly revenue
- Reports page (fleet, contracts, and branch revenue snapshot)
- One-click demo data bootstrap from the top navbar

## Quick Start

1. (Optional) Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   python app.py
   ```

4. Open:

   ```text
   http://127.0.0.1:5000
   ```

The app creates a local SQLite database automatically on first run.

### Link Flask app with GPS backend

To enable full GPSDome integration in this Flask app, set:

```bash
export GPS_BACKEND_BASE_URL="http://127.0.0.1:8080"
```

Then the app will:

- Sync contracts to Node GPS backend on start/close
- Allow GPS live sync from the GPS page
- Show per-contract GPS reports

## Deploy on Web (Render - Free Tier)

Use the one-click button:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/a8a8a30-cyber/atlassian-mcp-server/tree/cursor%2F-bc-8b68025c-17d0-4110-b575-fabd34492e23-825c)

Or deploy manually:

1. Open https://render.com and sign in.
2. Click **New +** -> **Blueprint**.
3. Select this repository.
4. Render will detect `render.yaml` automatically and create:
   - `car-rental-admin` (Flask app)
   - `car-rental-gps-backend` (Node GPS integration)
5. Fill required environment values for **car-rental-gps-backend**:
   - `MYSQL_HOST`
   - `MYSQL_DATABASE`
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `GPSDOME_EMAIL`
   - `GPSDOME_PASSWORD`
6. In **car-rental-admin** service, set:
   - `GPS_BACKEND_BASE_URL=<your car-rental-gps-backend public URL>`
7. Redeploy both services after saving env vars.
8. Open Flask URL and test:
   - Start a contract with a vehicle that has IMEI in `GPS ID`
   - Open contract GPS report
   - Open GPS page and run "مزامنة الآن"

Health check endpoint:

```text
/health
```

Notes:

- Free tier services may sleep after inactivity.
- SQLite storage on free web instances is not durable across full redeploys.
- For production persistence, configure a managed PostgreSQL database and set
  `DATABASE_URL`.
- GPS backend requires MySQL (external service or your own managed MySQL).

## Run Tests

```bash
python -m unittest discover -s tests -v
```

## Next Suggested Steps

- Add authentication and role-based access control
- Integrate real GPS provider webhook/API instead of manual points
- Add branch transfer workflows and maintenance ticketing details
- Add printable contract templates (Arabic/English)
- Add PostgreSQL migration for long-term data durability

## GPSDome Node Backend (new)

For production GPS integration with Node.js + Express + MySQL, use:

```text
gps-backend/
```

See:

```text
gps-backend/README.md
```