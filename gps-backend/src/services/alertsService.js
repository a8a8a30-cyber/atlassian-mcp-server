const { query } = require("../db/mysql");
const { logger } = require("../lib/logger");

class AlertsService {
  constructor({ contractsService, syncService }) {
    this.contractsService = contractsService;
    this.syncService = syncService;
  }

  async alertExistsRecently({ contractId, alertType, minutesWindow }) {
    const rows = await query(
      `
        SELECT id
        FROM contract_alerts
        WHERE contract_id = :contractId
          AND alert_type = :alertType
          AND created_at >= DATE_SUB(UTC_TIMESTAMP(), INTERVAL :minutesWindow MINUTE)
        LIMIT 1
      `,
      { contractId, alertType, minutesWindow }
    );
    return rows.length > 0;
  }

  async createAlert({
    contractId,
    imei,
    alertType,
    thresholdValue,
    actualValue,
    message,
    positionId = null,
    metadata = {},
  }) {
    await query(
      `
        INSERT INTO contract_alerts (
          contract_id,
          imei,
          alert_type,
          threshold_value,
          actual_value,
          message,
          position_id,
          metadata
        )
        VALUES (
          :contractId,
          :imei,
          :alertType,
          :thresholdValue,
          :actualValue,
          :message,
          :positionId,
          :metadata
        )
      `,
      {
        contractId,
        imei,
        alertType,
        thresholdValue,
        actualValue,
        message,
        positionId,
        metadata: JSON.stringify(metadata),
      }
    );
  }

  async runContractAlerts(contract) {
    let speedAlerts = 0;
    let distanceAlerts = 0;

    const latestPosition = await this.syncService.latestPositionByImei(contract.deviceImei);
    if (latestPosition) {
      const speed = Number(latestPosition.speed_kmh || 0);
      if (speed > contract.speedLimitKmh) {
        const exists = await this.alertExistsRecently({
          contractId: contract.id,
          alertType: "speed",
          minutesWindow: 20,
        });
        if (!exists) {
          await this.createAlert({
            contractId: contract.id,
            imei: contract.deviceImei,
            alertType: "speed",
            thresholdValue: contract.speedLimitKmh,
            actualValue: speed,
            message: `تجاوز سرعة العقد (${speed.toFixed(
              1
            )} كم/س > الحد ${contract.speedLimitKmh} كم/س).`,
            positionId: latestPosition.id,
            metadata: {
              positionTime: latestPosition.position_time,
              latitude: Number(latestPosition.latitude),
              longitude: Number(latestPosition.longitude),
            },
          });
          speedAlerts += 1;
        }
      }
    }

    const distance = await this.syncService.calculateContractDistance(contract.id);
    if (Number(distance.distanceKm) > Number(contract.distanceLimitKm)) {
      const exists = await this.alertExistsRecently({
        contractId: contract.id,
        alertType: "distance",
        minutesWindow: 120,
      });
      if (!exists) {
        await this.createAlert({
          contractId: contract.id,
          imei: contract.deviceImei,
          alertType: "distance",
          thresholdValue: Number(contract.distanceLimitKm),
          actualValue: Number(distance.distanceKm),
          message: `تجاوز مسافة العقد (${Number(distance.distanceKm).toFixed(
            2
          )} كم > الحد ${Number(contract.distanceLimitKm).toFixed(2)} كم).`,
          metadata: {
            source: distance.source,
          },
        });
        distanceAlerts += 1;
      }
    }

    return { speedAlerts, distanceAlerts };
  }

  async runAllAlerts() {
    const activeContracts = await this.contractsService.activeContracts();
    let speedAlerts = 0;
    let distanceAlerts = 0;
    for (const contract of activeContracts) {
      try {
        const result = await this.runContractAlerts(contract);
        speedAlerts += result.speedAlerts;
        distanceAlerts += result.distanceAlerts;
      } catch (error) {
        logger.error("Failed evaluating contract alerts", {
          contractId: contract.id,
          error: error.message,
        });
      }
    }
    return {
      activeContracts: activeContracts.length,
      speedAlerts,
      distanceAlerts,
    };
  }

  async listAlertsByContract(contractId, { limit = 200 } = {}) {
    return query(
      `
        SELECT id, contract_id, imei, alert_type, threshold_value, actual_value, message, metadata, created_at
        FROM contract_alerts
        WHERE contract_id = :contractId
        ORDER BY created_at DESC
        LIMIT :limit
      `,
      { contractId, limit: Number(limit) }
    );
  }
}

module.exports = { AlertsService };
