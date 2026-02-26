const test = require("node:test");
const assert = require("node:assert/strict");

const {
  extractToken,
  normalizeDevice,
  normalizePosition,
  extractDistanceKm,
} = require("../src/lib/normalizers");

test("extractToken reads nested API token", () => {
  const token = extractToken({ data: { token: "abc123" } });
  assert.equal(token, "abc123");
});

test("normalizeDevice maps external fields", () => {
  const normalized = normalizeDevice({
    id: 22,
    imei: "862476053522545",
    name: "Concox-01",
    protocol: "GT06",
  });

  assert.equal(normalized.externalDeviceId, "22");
  assert.equal(normalized.imei, "862476053522545");
  assert.equal(normalized.protocol, "GT06");
});

test("normalizePosition supports lat/lon and speed", () => {
  const normalized = normalizePosition({
    id: "p-1",
    deviceId: "22",
    imei: "862476053522545",
    lat: 24.7136,
    lon: 46.6753,
    speed: 88,
    timestamp: "2026-02-26T10:00:00Z",
  });

  assert.equal(normalized.externalPositionId, "p-1");
  assert.equal(normalized.latitude, 24.7136);
  assert.equal(normalized.longitude, 46.6753);
  assert.equal(normalized.speedKmh, 88);
});

test("extractDistanceKm returns summary distance", () => {
  const distance = extractDistanceKm({ result: { totalDistance: 55.8 } });
  assert.equal(distance, 55.8);
});
