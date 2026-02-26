# Car Rental Admin MVP (Low Cost)

This repository now contains a lightweight internal car rental management system
built for fast deployment and zero license cost.

## Stack

- Python 3.12
- Flask
- Flask-SQLAlchemy
- SQLite (default local database)
- Bootstrap 5 (CDN)

## Included MVP Features

- Branch management
- Fleet management (vehicles, status, daily rates, GPS device ID)
- Reservation management with overlap validation
- Contract lifecycle (start/close contract)
- Basic GPS point logging (manual input for now)
- Dashboard with operational counters

## Quick Start

1. Create and activate a virtual environment:

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

The app creates `car_rental.db` automatically on first run.

## Run Tests

```bash
python -m unittest discover -s tests -v
```

## Next Suggested Steps

- Add authentication and role-based access control
- Integrate real GPS provider webhook/API instead of manual points
- Add branch transfer workflows and maintenance ticketing details
- Add printable contract templates (Arabic/English)
- Deploy on low-cost VPS (Ubuntu + Gunicorn + Nginx)