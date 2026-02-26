const { env } = require("./config/env");
const { logger } = require("./lib/logger");
const { initSchema } = require("./db/initSchema");
const { createApp } = require("./app");
const { startScheduler } = require("./cron/scheduler");

async function bootstrap() {
  await initSchema();

  const { app, services } = createApp();
  const server = app.listen(env.port, () => {
    logger.info("GPS backend listening", { port: env.port });
  });

  let scheduler = null;
  if (env.enableCron) {
    scheduler = startScheduler(services);
  }

  const shutdown = async (signal) => {
    logger.info("Shutdown signal received", { signal });
    if (scheduler) {
      scheduler.stopAll();
    }
    server.close(() => {
      logger.info("HTTP server closed");
      process.exit(0);
    });
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

bootstrap().catch((error) => {
  logger.error("Failed to bootstrap backend", { error: error.message });
  process.exit(1);
});
