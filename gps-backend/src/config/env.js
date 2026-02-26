const path = require("node:path");
const dotenv = require("dotenv");

dotenv.config({ path: path.resolve(process.cwd(), ".env") });

function asBoolean(value, fallback = false) {
  if (value === undefined) return fallback;
  return String(value).toLowerCase() === "true";
}

function asInt(value, fallback) {
  const parsed = Number.parseInt(value, 10);
  return Number.isNaN(parsed) ? fallback : parsed;
}

function asFloat(value, fallback) {
  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? fallback : parsed;
}

const env = {
  nodeEnv: process.env.NODE_ENV || "development",
  port: asInt(process.env.PORT, 8080),
  enableCron: asBoolean(process.env.ENABLE_CRON, true),
  strictDbStartup: asBoolean(process.env.STRICT_DB_STARTUP, false),

  mysql: {
    host: process.env.MYSQL_HOST || "127.0.0.1",
    port: asInt(process.env.MYSQL_PORT, 3306),
    database: process.env.MYSQL_DATABASE || "car_rental_gps",
    user: process.env.MYSQL_USER || "root",
    password: process.env.MYSQL_PASSWORD || "",
    connectionLimit: asInt(process.env.MYSQL_CONNECTION_LIMIT, 10),
    connectTimeoutMs: asInt(process.env.MYSQL_CONNECT_TIMEOUT_MS, 5000),
  },

  gpsdome: {
    baseUrl: process.env.GPSDOME_BASE_URL || "https://track.gpsdome.net",
    sessionEndpoint: process.env.GPSDOME_SESSION_ENDPOINT || "/api/session",
    devicesEndpoint: process.env.GPSDOME_DEVICES_ENDPOINT || "/api/devices",
    positionsEndpoint: process.env.GPSDOME_POSITIONS_ENDPOINT || "/api/positions",
    reportsSummaryEndpoint:
      process.env.GPSDOME_REPORTS_SUMMARY_ENDPOINT || "/api/reports/summary",
    email: process.env.GPSDOME_EMAIL || "",
    password: process.env.GPSDOME_PASSWORD || "",
    useBasicAuth: asBoolean(process.env.GPSDOME_USE_BASIC_AUTH, false),
    requestTimeoutMs: asInt(process.env.GPSDOME_REQUEST_TIMEOUT_MS, 20000),
  },

  jobs: {
    syncCron: process.env.GPS_SYNC_CRON || "*/2 * * * *",
    alertsCron: process.env.GPS_ALERT_CRON || "*/3 * * * *",
  },

  defaults: {
    speedLimitKmh: asInt(process.env.DEFAULT_SPEED_LIMIT_KMH, 120),
    distanceLimitKm: asFloat(process.env.DEFAULT_DISTANCE_LIMIT_KM, 500),
  },
};

module.exports = { env };
