const express = require("express");
const { asyncHandler } = require("./utils");

function createGpsRoutes({ gpsClient, syncService }) {
  const router = express.Router();

  router.post(
    "/auth",
    asyncHandler(async (req, res) => {
      const session = await gpsClient.authenticate(true);
      res.json({
        ok: true,
        session: {
          tokenReceived: Boolean(session.token),
          cookieReceived: Boolean(session.cookie),
          expiresAt: session.expiresAt,
        },
      });
    })
  );

  router.get(
    "/devices",
    asyncHandler(async (req, res) => {
      const devices = await gpsClient.getDevices();
      if (req.query.sync === "true") {
        const syncResult = await syncService.syncDevices();
        return res.json({ ok: true, devices, syncResult });
      }
      return res.json({ ok: true, devices });
    })
  );

  router.get(
    "/positions",
    asyncHandler(async (req, res) => {
      const positions = await gpsClient.getPositions({
        from: req.query.from,
        to: req.query.to,
        deviceId: req.query.deviceId,
        imei: req.query.imei,
        limit: req.query.limit,
      });

      if (req.query.sync === "true") {
        const syncResult = await syncService.syncPositions({
          fromMinutes: Number(req.query.fromMinutes || 10),
          limit: Number(req.query.limit || 500),
        });
        return res.json({ ok: true, positions, syncResult });
      }
      return res.json({ ok: true, positions });
    })
  );

  router.get(
    "/reports/summary",
    asyncHandler(async (req, res) => {
      const summary = await gpsClient.getDistanceSummary({
        from: req.query.from,
        to: req.query.to,
        deviceId: req.query.deviceId,
        imei: req.query.imei,
      });

      return res.json({
        ok: true,
        distanceKm: summary.distanceKm,
        raw: summary.raw,
      });
    })
  );

  router.post(
    "/sync/devices",
    asyncHandler(async (_req, res) => {
      const result = await syncService.syncDevices();
      res.json({ ok: true, result });
    })
  );

  router.post(
    "/sync/positions",
    asyncHandler(async (req, res) => {
      const result = await syncService.syncPositions({
        fromMinutes: Number(req.body.fromMinutes || 10),
        limit: Number(req.body.limit || 500),
      });
      res.json({ ok: true, result });
    })
  );

  return router;
}

module.exports = { createGpsRoutes };
