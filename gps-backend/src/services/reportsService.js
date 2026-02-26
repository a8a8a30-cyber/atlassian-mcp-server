const { query } = require("../db/mysql");

class ReportsService {
  constructor({ contractsService, syncService, alertsService }) {
    this.contractsService = contractsService;
    this.syncService = syncService;
    this.alertsService = alertsService;
  }

  async contractReport(contractId) {
    const contract = await this.contractsService.getContract(contractId);
    if (!contract) {
      return null;
    }

    const latestPosition = await this.syncService.latestPositionByImei(contract.deviceImei);
    const distance = await this.syncService.calculateContractDistance(contract.id);
    const alerts = await this.alertsService.listAlertsByContract(contract.id, { limit: 100 });
    const positions = await this.syncService.getPositionsForContract(contract.id, { limit: 1500 });

    const totalPositions = positions.length;
    let maxSpeed = 0;
    let averageSpeed = 0;
    if (totalPositions > 0) {
      const speeds = positions.map((position) => Number(position.speed_kmh || 0));
      maxSpeed = Math.max(...speeds);
      averageSpeed = speeds.reduce((sum, speed) => sum + speed, 0) / speeds.length;
    }

    return {
      contract,
      latestPosition,
      distance,
      alerts,
      metrics: {
        totalPositions,
        maxSpeedKmh: Number(maxSpeed.toFixed(2)),
        averageSpeedKmh: Number(averageSpeed.toFixed(2)),
      },
      timeline: positions.map((position) => ({
        id: position.id,
        latitude: Number(position.latitude),
        longitude: Number(position.longitude),
        speedKmh: Number(position.speed_kmh),
        at: position.position_time,
      })),
    };
  }

  async summary() {
    const [totals] = await query(
      `
        SELECT
          COUNT(*) AS contracts_total,
          SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS contracts_active,
          SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) AS contracts_closed
        FROM rental_contracts
      `
    );

    const [alerts] = await query(
      `
        SELECT
          COUNT(*) AS alerts_total,
          SUM(CASE WHEN alert_type = 'speed' THEN 1 ELSE 0 END) AS speed_alerts,
          SUM(CASE WHEN alert_type = 'distance' THEN 1 ELSE 0 END) AS distance_alerts
        FROM contract_alerts
      `
    );

    const latestSyncRuns = await query(
      `
        SELECT id, job_name, status, started_at, finished_at, message
        FROM sync_runs
        ORDER BY started_at DESC
        LIMIT 20
      `
    );

    return {
      contracts: totals,
      alerts,
      latestSyncRuns,
    };
  }
}

module.exports = { ReportsService };
