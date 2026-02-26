const { query } = require("../db/mysql");
const { logger } = require("../lib/logger");
const { totalDistanceKm } = require("../lib/distance");
const {
  normalizeDateTime,
  normalizeDevice,
  normalizePosition,
} = require("../lib/normalizers");

class SyncService {
  constructor({ gpsClient, contractsService }) {
    this.gpsClient = gpsClient;
    this.contractsService = contractsService;
  }

  async startSyncRun(jobName) {
    const result = await query(
      `
        INSERT INTO sync_runs (job_name, status, started_at)
        VALUES (:jobName, 'running', UTC_TIMESTAMP())
      `,
      { jobName }
    );
    return result.insertId;
  }

  async finishSyncRun(runId, status, message = null) {
    await query(
      `
        UPDATE sync_runs
        SET status = :status,
            finished_at = UTC_TIMESTAMP(),
            message = :message
        WHERE id = :runId
      `,
      { runId, status, message }
    );
  }

  async loadDeviceMap() {
    const rows = await query(
      `
        SELECT external_device_id, imei
        FROM gps_devices
      `
    );
    const map = new Map();
    for (const row of rows) {
      map.set(row.external_device_id, { imei: row.imei });
    }
    return map;
  }

  async upsertDevice(normalizedDevice) {
    await query(
      `
        INSERT INTO gps_devices (
          external_device_id,
          imei,
          name,
          device_type,
          protocol,
          last_position_at,
          raw_payload
        )
        VALUES (
          :externalDeviceId,
          :imei,
          :name,
          :deviceType,
          :protocol,
          :lastPositionAt,
          :rawPayload
        )
        ON DUPLICATE KEY UPDATE
          imei = VALUES(imei),
          name = VALUES(name),
          device_type = VALUES(device_type),
          protocol = VALUES(protocol),
          last_position_at = VALUES(last_position_at),
          raw_payload = VALUES(raw_payload),
          updated_at = UTC_TIMESTAMP()
      `,
      {
        externalDeviceId: normalizedDevice.externalDeviceId,
        imei: normalizedDevice.imei,
        name: normalizedDevice.name,
        deviceType: normalizedDevice.deviceType,
        protocol: normalizedDevice.protocol,
        lastPositionAt: normalizedDevice.lastPositionAt,
        rawPayload: JSON.stringify(normalizedDevice.rawPayload),
      }
    );
  }

  async upsertPosition(normalizedPosition) {
    await query(
      `
        INSERT INTO gps_positions (
          external_position_id,
          external_device_id,
          imei,
          latitude,
          longitude,
          speed_kmh,
          heading,
          altitude_m,
          position_time,
          raw_payload
        )
        VALUES (
          :externalPositionId,
          :externalDeviceId,
          :imei,
          :latitude,
          :longitude,
          :speedKmh,
          :heading,
          :altitudeM,
          :positionTime,
          :rawPayload
        )
        ON DUPLICATE KEY UPDATE
          speed_kmh = VALUES(speed_kmh),
          heading = VALUES(heading),
          altitude_m = VALUES(altitude_m),
          raw_payload = VALUES(raw_payload)
      `,
      {
        externalPositionId: normalizedPosition.externalPositionId,
        externalDeviceId: normalizedPosition.externalDeviceId,
        imei: normalizedPosition.imei,
        latitude: normalizedPosition.latitude,
        longitude: normalizedPosition.longitude,
        speedKmh: normalizedPosition.speedKmh,
        heading: normalizedPosition.heading,
        altitudeM: normalizedPosition.altitudeM,
        positionTime: normalizedPosition.positionTime,
        rawPayload: JSON.stringify(normalizedPosition.rawPayload),
      }
    );
  }

  async syncDevices() {
    const runId = await this.startSyncRun("sync_devices");
    try {
      const rawDevices = await this.gpsClient.getDevices();
      let processed = 0;
      for (const raw of rawDevices) {
        const normalized = normalizeDevice(raw);
        if (!normalized) continue;
        await this.upsertDevice(normalized);
        processed += 1;
      }

      await this.finishSyncRun(runId, "success", `Processed ${processed} devices`);
      return { processed, sourceCount: rawDevices.length };
    } catch (error) {
      await this.finishSyncRun(runId, "failed", error.message);
      logger.error("Failed syncing devices", { error: error.message });
      throw error;
    }
  }

  async syncPositions({ fromMinutes = 10, limit = 500 } = {}) {
    const runId = await this.startSyncRun("sync_positions");
    try {
      const fromDate = new Date(Date.now() - fromMinutes * 60 * 1000);
      const rawPositions = await this.gpsClient.getPositions({
        from: fromDate.toISOString(),
        limit,
      });

      const deviceMap = await this.loadDeviceMap();
      let processed = 0;
      for (const raw of rawPositions) {
        const normalized = normalizePosition(raw, deviceMap);
        if (!normalized) continue;
        await this.upsertPosition(normalized);
        processed += 1;
      }

      await this.finishSyncRun(runId, "success", `Processed ${processed} positions`);
      return { processed, sourceCount: rawPositions.length };
    } catch (error) {
      await this.finishSyncRun(runId, "failed", error.message);
      logger.error("Failed syncing positions", { error: error.message });
      throw error;
    }
  }

  async getPositionsForContract(contractId, { limit = 2000 } = {}) {
    const contract = await this.contractsService.getContract(contractId);
    if (!contract) {
      throw new Error(`Contract ${contractId} not found`);
    }

    const endBoundary = contract.actualEndAt || contract.endAt || new Date();
    return query(
      `
        SELECT id, imei, latitude, longitude, speed_kmh, position_time
        FROM gps_positions
        WHERE imei = :imei
          AND position_time >= :startAt
          AND position_time <= :endAt
        ORDER BY position_time ASC
        LIMIT :limit
      `,
      {
        imei: contract.deviceImei,
        startAt: normalizeDateTime(contract.startAt),
        endAt: normalizeDateTime(endBoundary),
        limit: Number(limit),
      }
    );
  }

  async calculateDistanceFromStoredPositions(contractId) {
    const points = await this.getPositionsForContract(contractId);
    const normalizedPoints = points.map((row) => ({
      latitude: Number(row.latitude),
      longitude: Number(row.longitude),
    }));
    return {
      distanceKm: totalDistanceKm(normalizedPoints),
      pointsCount: points.length,
    };
  }

  async saveDistanceSnapshot(contractId, distanceKm, source, details = {}) {
    await query(
      `
        INSERT INTO contract_distance_snapshots (
          contract_id,
          distance_km,
          source,
          details
        )
        VALUES (
          :contractId,
          :distanceKm,
          :source,
          :details
        )
      `,
      {
        contractId,
        distanceKm,
        source,
        details: JSON.stringify(details),
      }
    );
  }

  async calculateContractDistance(contractId) {
    const contract = await this.contractsService.getContract(contractId);
    if (!contract) {
      throw new Error(`Contract ${contractId} not found`);
    }

    const from = normalizeDateTime(contract.startAt) || new Date();
    const to =
      normalizeDateTime(contract.actualEndAt) ||
      normalizeDateTime(contract.endAt) ||
      new Date();

    try {
      const summary = await this.gpsClient.getDistanceSummary({
        from: from.toISOString(),
        to: to.toISOString(),
        imei: contract.deviceImei,
      });
      if (summary.distanceKm !== null) {
        await this.saveDistanceSnapshot(
          contract.id,
          summary.distanceKm,
          "gpsdome_summary",
          { from: from.toISOString(), to: to.toISOString() }
        );
        return {
          contractId: contract.id,
          source: "gpsdome_summary",
          distanceKm: Number(summary.distanceKm),
          raw: summary.raw,
        };
      }
    } catch (error) {
      logger.warn("GPSDome summary unavailable, using local fallback", {
        contractId: contract.id,
        error: error.message,
      });
    }

    const fallback = await this.calculateDistanceFromStoredPositions(contract.id);
    await this.saveDistanceSnapshot(
      contract.id,
      fallback.distanceKm,
      "positions_fallback",
      { pointsCount: fallback.pointsCount }
    );
    return {
      contractId: contract.id,
      source: "positions_fallback",
      distanceKm: Number(fallback.distanceKm),
      pointsCount: fallback.pointsCount,
    };
  }

  async latestPositionByImei(imei) {
    const rows = await query(
      `
        SELECT id, imei, latitude, longitude, speed_kmh, heading, position_time
        FROM gps_positions
        WHERE imei = :imei
        ORDER BY position_time DESC
        LIMIT 1
      `,
      { imei }
    );
    return rows[0] || null;
  }
}

module.exports = { SyncService };
