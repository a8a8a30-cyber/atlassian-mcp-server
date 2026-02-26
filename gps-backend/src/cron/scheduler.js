const cron = require("node-cron");
const { env } = require("../config/env");
const { logger } = require("../lib/logger");

function startScheduler({ syncService, alertsService }) {
  const jobs = [];

  const syncJob = cron.schedule(env.jobs.syncCron, async () => {
    try {
      const devices = await syncService.syncDevices();
      const positions = await syncService.syncPositions({ fromMinutes: 10, limit: 1000 });
      logger.info("GPS sync job done", { devices, positions });
    } catch (error) {
      logger.error("GPS sync job failed", { error: error.message });
    }
  });

  jobs.push(syncJob);

  const alertsJob = cron.schedule(env.jobs.alertsCron, async () => {
    try {
      const result = await alertsService.runAllAlerts();
      logger.info("Alerts job done", result);
    } catch (error) {
      logger.error("Alerts job failed", { error: error.message });
    }
  });

  jobs.push(alertsJob);

  logger.info("Cron scheduler started", {
    syncCron: env.jobs.syncCron,
    alertsCron: env.jobs.alertsCron,
  });

  return {
    stopAll() {
      for (const job of jobs) {
        job.stop();
      }
    },
  };
}

module.exports = { startScheduler };
