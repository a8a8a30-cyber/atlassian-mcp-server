const { env } = require("../config/env");
const { query } = require("../db/mysql");

function mapContract(row) {
  if (!row) return null;
  return {
    id: row.id,
    externalContractId: row.external_contract_id,
    customerName: row.customer_name,
    vehiclePlate: row.vehicle_plate,
    deviceImei: row.device_imei,
    startAt: row.start_at,
    endAt: row.end_at,
    actualEndAt: row.actual_end_at,
    speedLimitKmh: row.speed_limit_kmh,
    distanceLimitKm: Number(row.distance_limit_km),
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

class ContractsService {
  async listContracts({ status } = {}) {
    const filters = [];
    const params = {};
    if (status) {
      filters.push("status = :status");
      params.status = status;
    }

    const whereSql = filters.length > 0 ? `WHERE ${filters.join(" AND ")}` : "";
    const rows = await query(
      `
        SELECT *
        FROM rental_contracts
        ${whereSql}
        ORDER BY created_at DESC
      `,
      params
    );
    return rows.map(mapContract);
  }

  async getContract(contractId) {
    const rows = await query(
      `
        SELECT *
        FROM rental_contracts
        WHERE id = :contractId
        LIMIT 1
      `,
      { contractId }
    );
    return mapContract(rows[0]);
  }

  async getContractByExternalId(externalContractId) {
    const rows = await query(
      `
        SELECT *
        FROM rental_contracts
        WHERE external_contract_id = :externalContractId
        LIMIT 1
      `,
      { externalContractId }
    );
    return mapContract(rows[0]);
  }

  async createContract(payload) {
    const data = {
      externalContractId: payload.externalContractId,
      customerName: payload.customerName || null,
      vehiclePlate: payload.vehiclePlate || null,
      deviceImei: payload.deviceImei,
      startAt: payload.startAt,
      endAt: payload.endAt || null,
      speedLimitKmh: payload.speedLimitKmh || env.defaults.speedLimitKmh,
      distanceLimitKm: payload.distanceLimitKm || env.defaults.distanceLimitKm,
    };

    await query(
      `
        INSERT INTO rental_contracts (
          external_contract_id,
          customer_name,
          vehicle_plate,
          device_imei,
          start_at,
          end_at,
          speed_limit_kmh,
          distance_limit_km
        )
        VALUES (
          :externalContractId,
          :customerName,
          :vehiclePlate,
          :deviceImei,
          :startAt,
          :endAt,
          :speedLimitKmh,
          :distanceLimitKm
        )
      `,
      data
    );

    return this.getContractByExternalId(payload.externalContractId);
  }

  async closeContract(contractId) {
    await query(
      `
        UPDATE rental_contracts
        SET status = 'closed',
            actual_end_at = UTC_TIMESTAMP()
        WHERE id = :contractId
      `,
      { contractId }
    );
    return this.getContract(contractId);
  }

  async closeContractByExternalId(externalContractId) {
    const contract = await this.getContractByExternalId(externalContractId);
    if (!contract) {
      return null;
    }
    return this.closeContract(contract.id);
  }

  async activeContracts() {
    return this.listContracts({ status: "active" });
  }
}

module.exports = { ContractsService };
