const express = require("express");
const { asyncHandler } = require("./utils");

function createReportRoutes({ reportsService, syncService, alertsService, contractsService }) {
  const router = express.Router();

  router.get(
    "/summary",
    asyncHandler(async (_req, res) => {
      const summary = await reportsService.summary();
      res.json({ ok: true, summary });
    })
  );

  router.get(
    "/contracts/:contractId",
    asyncHandler(async (req, res) => {
      const report = await reportsService.contractReport(Number(req.params.contractId));
      if (!report) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      return res.json({ ok: true, report });
    })
  );

  router.post(
    "/alerts/run",
    asyncHandler(async (_req, res) => {
      const result = await alertsService.runAllAlerts();
      res.json({ ok: true, result });
    })
  );

  router.post(
    "/contracts/:contractId/distance",
    asyncHandler(async (req, res) => {
      const contract = await contractsService.getContract(Number(req.params.contractId));
      if (!contract) {
        return res.status(404).json({ ok: false, error: "Contract not found" });
      }
      const result = await syncService.calculateContractDistance(contract.id);
      return res.json({ ok: true, result });
    })
  );

  return router;
}

module.exports = { createReportRoutes };
