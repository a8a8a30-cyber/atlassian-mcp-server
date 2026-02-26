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

  async contractReportByExternalId(externalContractId) {
    const contract = await this.contractsService.getContractByExternalId(
      externalContractId
    );
    if (!contract) {
      return null;
    }
    return this.contractReport(contract.id);
  }

  async latestPositions({ limit = 100 } = {}) {
    const rows = await query(
      `
        SELECT
          p.id,
          p.external_device_id,
          p.imei,
          p.latitude,
          p.longitude,
          p.speed_kmh,
          p.heading,
          p.position_time,
          d.name AS device_name,
          c.id AS active_contract_id,
          c.external_contract_id AS active_external_contract_id,
          c.customer_name AS active_customer_name,
          c.vehicle_plate AS active_vehicle_plate
        FROM gps_positions p
        INNER JOIN (
          SELECT imei, MAX(position_time) AS max_time
          FROM gps_positions
          GROUP BY imei
        ) latest
          ON latest.imei = p.imei
          AND latest.max_time = p.position_time
        LEFT JOIN gps_devices d ON d.imei = p.imei
        LEFT JOIN rental_contracts c
          ON c.device_imei = p.imei
          AND c.status = 'active'
        ORDER BY p.position_time DESC
        LIMIT :limit
      `,
      { limit: Number(limit) }
    );

    return rows.map((row) => ({
      id: row.id,
      externalDeviceId: row.external_device_id,
      imei: row.imei,
      latitude: Number(row.latitude),
      longitude: Number(row.longitude),
      speedKmh: Number(row.speed_kmh),
      heading: Number(row.heading || 0),
      positionTime: row.position_time,
      deviceName: row.device_name,
      activeContract: row.active_contract_id
        ? {
            id: row.active_contract_id,
            externalContractId: row.active_external_contract_id,
            customerName: row.active_customer_name,
            vehiclePlate: row.active_vehicle_plate,
          }
        : null,
    }));
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
