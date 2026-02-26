const test = require("node:test");
const assert = require("node:assert/strict");

const { haversineDistanceKm, totalDistanceKm } = require("../src/lib/distance");

test("haversineDistanceKm returns ~326 km between Riyadh and Qassim", () => {
  const riyadh = { latitude: 24.7136, longitude: 46.6753 };
  const qassim = { latitude: 26.3592, longitude: 43.9818 };
  const distance = haversineDistanceKm(riyadh, qassim);
  assert.equal(distance > 300 && distance < 360, true);
});

test("totalDistanceKm sums consecutive segments", () => {
  const points = [
    { latitude: 24.7136, longitude: 46.6753 },
    { latitude: 24.7743, longitude: 46.7386 },
    { latitude: 24.8176, longitude: 46.7957 },
  ];

  const total = totalDistanceKm(points);
  assert.equal(total > 10, true);
});
