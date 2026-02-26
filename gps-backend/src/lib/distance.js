const EARTH_RADIUS_KM = 6371;

function toRadians(value) {
  return (value * Math.PI) / 180;
}

function haversineDistanceKm(pointA, pointB) {
  const latitudeDelta = toRadians(pointB.latitude - pointA.latitude);
  const longitudeDelta = toRadians(pointB.longitude - pointA.longitude);
  const latA = toRadians(pointA.latitude);
  const latB = toRadians(pointB.latitude);

  const sinLatitude = Math.sin(latitudeDelta / 2);
  const sinLongitude = Math.sin(longitudeDelta / 2);

  const calculation =
    sinLatitude * sinLatitude +
    Math.cos(latA) * Math.cos(latB) * sinLongitude * sinLongitude;
  const arc = 2 * Math.atan2(Math.sqrt(calculation), Math.sqrt(1 - calculation));

  return EARTH_RADIUS_KM * arc;
}

function totalDistanceKm(points) {
  if (!Array.isArray(points) || points.length < 2) {
    return 0;
  }

  let sum = 0;
  for (let index = 1; index < points.length; index += 1) {
    sum += haversineDistanceKm(points[index - 1], points[index]);
  }
  return Number(sum.toFixed(3));
}

module.exports = {
  haversineDistanceKm,
  totalDistanceKm,
};
