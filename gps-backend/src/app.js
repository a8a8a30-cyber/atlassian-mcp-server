const express = require("express");
const { env } = require("./config/env");
const { healthCheck } = require("./db/mysql");
const { logger } = require("./lib/logger");
const { GpsDomeClient } = require("./services/gpsdomeClient");
const { ContractsService } = require("./services/contractsService");
const { SyncService } = require("./services/syncService");
const { AlertsService } = require("./services/alertsService");
const { ReportsService } = require("./services/reportsService");
const { createGpsRoutes } = require("./routes/gpsRoutes");
const { createContractRoutes } = require("./routes/contractRoutes");
const { createReportRoutes } = require("./routes/reportRoutes");
const { createIntegrationRoutes } = require("./routes/integrationRoutes");

function createServices() {
  const gpsClient = new GpsDomeClient();
  const contractsService = new ContractsService();
  const syncService = new SyncService({ gpsClient, contractsService });
  const alertsService = new AlertsService({ contractsService, syncService });
  const reportsService = new ReportsService({
    contractsService,
    syncService,
    alertsService,
  });

  return {
    gpsClient,
    contractsService,
    syncService,
    alertsService,
    reportsService,
  };
}

function createApp(services = createServices()) {
  const app = express();

  app.use(express.json({ limit: "2mb" }));

  app.get("/health", async (_req, res) => {
    const mysqlOk = await healthCheck();
    res.json({
      ok: true,
      service: "gps-rental-backend",
      environment: env.nodeEnv,
      mysql: mysqlOk ? "up" : "down",
      time: new Date().toISOString(),
    });
  });

  app.use("/api/gpsdome", createGpsRoutes(services));
  app.use("/api/contracts", createContractRoutes(services));
  app.use("/api/reports", createReportRoutes(services));
  app.use("/api/integration", createIntegrationRoutes(services));

  app.use((req, res) => {
    res.status(404).json({
      ok: false,
      error: `Route not found: ${req.method} ${req.originalUrl}`,
    });
  });

  app.use((error, _req, res, _next) => {
    logger.error("Unhandled API error", {
      error: error.message,
      stack: env.nodeEnv === "development" ? error.stack : undefined,
    });
    res.status(500).json({
      ok: false,
      error: error.message || "Internal server error",
    });
  });

  return { app, services };
}

module.exports = { createApp };
