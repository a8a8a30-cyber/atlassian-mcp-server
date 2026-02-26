const express = require("express");
const { asyncHandler, requiredFields } = require("./utils");
const { env } = require("../config/env");

function createIntegrationRoutes({ contractsService }) {
  const router = express.Router();

  // This endpoint is designed for a rental system to push contracts to GPS backend.
  router.post(
    "/rental/contracts",
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
        return res.json({ ok: true, contract: existing, created: false });
      }

      const startAt = new Date(req.body.startAt);
      const endAt = req.body.endAt ? new Date(req.body.endAt) : null;
      if (Number.isNaN(startAt.getTime()) || (endAt && Number.isNaN(endAt.getTime()))) {
        return res.status(400).json({
          ok: false,
          error: "startAt/endAt must be valid ISO datetime values",
        });
      }

      const contract = await contractsService.createContract({
        externalContractId: req.body.externalContractId,
        customerName: req.body.customerName,
        vehiclePlate: req.body.vehiclePlate,
        deviceImei: req.body.deviceImei,
        startAt: startAt.toISOString().slice(0, 19).replace("T", " "),
        endAt: endAt ? endAt.toISOString().slice(0, 19).replace("T", " ") : null,
        speedLimitKmh: req.body.speedLimitKmh || env.defaults.speedLimitKmh,
        distanceLimitKm: req.body.distanceLimitKm || env.defaults.distanceLimitKm,
      });

      return res.status(201).json({ ok: true, contract, created: true });
    })
  );

  return router;
}

module.exports = { createIntegrationRoutes };
