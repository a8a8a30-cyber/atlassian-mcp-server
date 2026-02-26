const express = require("express");
const { asyncHandler, requiredFields } = require("./utils");
const { env } = require("../config/env");

function createContractRoutes({ contractsService, alertsService }) {
  const router = express.Router();

  router.get(
    "/",
    asyncHandler(async (req, res) => {
      const contracts = await contractsService.listContracts({
        status: req.query.status,
      });
      res.json({ ok: true, contracts });
    })
  );

  router.post(
    "/",
    asyncHandler(async (req, res) => {
      const missing = requiredFields(req.body, [
        "externalContractId",
        "deviceImei",
        "startAt",
      ]);
      if (missing.length > 0) {
        return res.status(400).json({
          ok: false,
          error: "Missing required fields",
          missing,
        });
      }

      const existing = await contractsService.getContractByExternalId(
        req.body.externalContractId
      );
      if (existing) {
        return res.status(409).json({
          ok: false,
          error: "externalContractId already exists",
        });
      }

      const speedLimitKmh =
        req.body.speedLimitKmh !== undefined
          ? Number(req.body.speedLimitKmh)
          : env.defaults.speedLimitKmh;
      const distanceLimitKm =
        req.body.distanceLimitKm !== undefined
          ? Number(req.body.distanceLimitKm)
          : env.defaults.distanceLimitKm;
      const startAt = new Date(req.body.startAt);
      const endAt = req.body.endAt ? new Date(req.body.endAt) : null;

      if (Number.isNaN(startAt.getTime()) || (endAt && Number.isNaN(endAt.getTime()))) {
        return res.status(400).json({
          ok: false,
          error: "startAt/endAt must be valid ISO datetime values",
        });
      }
      if (!Number.isFinite(speedLimitKmh) || speedLimitKmh <= 0) {
        return res.status(400).json({
          ok: false,
          error: "speedLimitKmh must be a positive number",
        });
      }
      if (!Number.isFinite(distanceLimitKm) || distanceLimitKm <= 0) {
        return res.status(400).json({
          ok: false,
          error: "distanceLimitKm must be a positive number",
        });
      }

      const contract = await contractsService.createContract({
        externalContractId: req.body.externalContractId,
        customerName: req.body.customerName,
        vehiclePlate: req.body.vehiclePlate,
        deviceImei: req.body.deviceImei,
        startAt: startAt.toISOString().slice(0, 19).replace("T", " "),
        endAt: endAt ? endAt.toISOString().slice(0, 19).replace("T", " ") : null,
        speedLimitKmh,
        distanceLimitKm,
      });

      return res.status(201).json({ ok: true, contract });
    })
  );

  router.get(
    "/external/:externalContractId",
    asyncHandler(async (req, res) => {
      const contract = await contractsService.getContractByExternalId(
        req.params.externalContractId
      );
      if (!contract) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      return res.json({ ok: true, contract });
    })
  );

  router.get(
    "/:contractId",
    asyncHandler(async (req, res) => {
      const contract = await contractsService.getContract(Number(req.params.contractId));
      if (!contract) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      return res.json({ ok: true, contract });
    })
  );

  router.patch(
    "/external/:externalContractId/close",
    asyncHandler(async (req, res) => {
      const updated = await contractsService.closeContractByExternalId(
        req.params.externalContractId
      );
      if (!updated) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      return res.json({ ok: true, contract: updated });
    })
  );

  router.patch(
    "/:contractId/close",
    asyncHandler(async (req, res) => {
      const contract = await contractsService.getContract(Number(req.params.contractId));
      if (!contract) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      const updated = await contractsService.closeContract(contract.id);
      return res.json({ ok: true, contract: updated });
    })
  );

  router.post(
    "/:contractId/alerts/run",
    asyncHandler(async (req, res) => {
      const contract = await contractsService.getContract(Number(req.params.contractId));
      if (!contract) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      const result = await alertsService.runContractAlerts(contract);
      return res.json({ ok: true, result });
    })
  );

  router.get(
    "/:contractId/alerts",
    asyncHandler(async (req, res) => {
      const contract = await contractsService.getContract(Number(req.params.contractId));
      if (!contract) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      const alerts = await alertsService.listAlertsByContract(contract.id, {
        limit: Number(req.query.limit || 200),
      });
      return res.json({ ok: true, alerts });
    })
  );

  return router;
}

module.exports = { createContractRoutes };
