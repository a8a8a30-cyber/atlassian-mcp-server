# GPSDome Rental Integration Backend (Node.js + Express + MySQL)

Backend service to connect GPSDome tracking data with rental contracts.

## What this service includes

1. Authentication with GPSDome API (`/api/session`)
2. Devices sync (`/api/devices`)
3. Live positions sync (`/api/positions`)
4. Distance calculation from GPSDome summary (`/api/reports/summary`) with local fallback
5. Rental contract integration endpoint
6. Speed and distance alerts
7. Comprehensive report per rental contract

## Stack

- Node.js + Express
- MySQL (`mysql2`)
- Axios
- Node Cron

## Environment

Copy and fill environment values:

```bash
cp .env.example .env
```

Set the required values in `.env`:

- `GPSDOME_BASE_URL`
- `GPSDOME_EMAIL`
- `GPSDOME_PASSWORD`
- MySQL connection values

## Install & run

```bash
npm install
npm start
```

Dev mode:

```bash
npm run dev
```

## Deploy on Render

This repo root `render.yaml` already includes this service with:

- service name: `car-rental-gps-backend`
- root directory: `gps-backend`

Required env vars in Render:

- `MYSQL_HOST`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `GPSDOME_EMAIL`
- `GPSDOME_PASSWORD`

Recommended startup settings:

- `STRICT_DB_STARTUP=false` (service starts even if DB is temporarily unavailable)
- `MYSQL_CONNECT_TIMEOUT_MS=5000`

Optional defaults already in blueprint:

- `GPSDOME_BASE_URL=https://track.gpsdome.net`
- `GPSDOME_SESSION_ENDPOINT=/api/session`
- `GPSDOME_DEVICES_ENDPOINT=/api/devices`
- `GPSDOME_POSITIONS_ENDPOINT=/api/positions`
- `GPSDOME_REPORTS_SUMMARY_ENDPOINT=/api/reports/summary`

## Database schema

Schema is in:

```text
sql/schema.sql
```

It is auto-applied on startup.

## API quick reference

### Health

- `GET /health`

### GPSDome

- `POST /api/gpsdome/auth` test authentication
- `GET /api/gpsdome/devices?sync=true`
- `GET /api/gpsdome/positions?from=...&to=...&sync=true`
- `GET /api/gpsdome/reports/summary?imei=...&from=...&to=...`
- `POST /api/gpsdome/sync/devices`
- `POST /api/gpsdome/sync/positions`

### Rental contracts

- `POST /api/contracts`
- `GET /api/contracts`
- `GET /api/contracts/:contractId`
- `GET /api/contracts/external/:externalContractId`
- `PATCH /api/contracts/:contractId/close`
- `PATCH /api/contracts/external/:externalContractId/close`
- `GET /api/contracts/:contractId/alerts`
- `POST /api/contracts/:contractId/alerts/run`

### Rental system integration

- `POST /api/integration/rental/contracts`

Example request:

```json
{
  "externalContractId": "RENT-2026-001",
  "customerName": "شركة دوس",
  "vehiclePlate": "ر س أ 1234",
  "deviceImei": "862476053522545",
  "startAt": "2026-02-26T08:00:00Z",
  "endAt": "2026-03-05T08:00:00Z",
  "speedLimitKmh": 120,
  "distanceLimitKm": 800
}
```

### Reports

- `GET /api/reports/summary`
- `GET /api/reports/contracts/:contractId`
- `GET /api/reports/contracts/external/:externalContractId`
- `GET /api/reports/live-positions`
- `POST /api/reports/contracts/:contractId/distance`
- `POST /api/reports/contracts/external/:externalContractId/distance`
- `POST /api/reports/alerts/run`

## Cron jobs

Configured from `.env`:

- `GPS_SYNC_CRON` for devices/positions sync
- `GPS_ALERT_CRON` for alert checks
