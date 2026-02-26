function extractDataArray(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (!payload || typeof payload !== "object") {
    return [];
  }

  const candidateKeys = [
    "data",
    "items",
    "result",
    "devices",
    "positions",
    "rows",
  ];

  for (const key of candidateKeys) {
    if (Array.isArray(payload[key])) {
      return payload[key];
    }
    if (payload[key] && typeof payload[key] === "object") {
      const nested = payload[key];
      for (const nestedKey of candidateKeys) {
        if (Array.isArray(nested[nestedKey])) {
          return nested[nestedKey];
        }
      }
    }
  }
  return [];
}

function extractToken(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const candidatePaths = [
    ["token"],
    ["accessToken"],
    ["sessionId"],
    ["session", "token"],
    ["data", "token"],
    ["data", "accessToken"],
    ["result", "token"],
  ];

  for (const path of candidatePaths) {
    let cursor = payload;
    for (const segment of path) {
      if (!cursor || typeof cursor !== "object") {
        cursor = undefined;
        break;
      }
      cursor = cursor[segment];
    }
    if (cursor && typeof cursor === "string") {
      return cursor;
    }
  }
  return null;
}

function normalizeDateTime(value) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date;
}

function normalizeDevice(raw) {
  const externalDeviceId = String(
    raw?.id ?? raw?.deviceId ?? raw?.device_id ?? raw?.uuid ?? ""
  ).trim();
  const imei = String(
    raw?.imei ?? raw?.IMEI ?? raw?.uniqueId ?? raw?.unique_id ?? ""
  ).trim();
  if (!externalDeviceId || !imei) {
    return null;
  }

  const lastPositionAt = normalizeDateTime(
    raw?.lastPositionAt ??
      raw?.lastUpdate ??
      raw?.lastSeen ??
      raw?.lastConnection ??
      null
  );

  return {
    externalDeviceId,
    imei,
    name: String(raw?.name ?? raw?.deviceName ?? raw?.alias ?? "").trim() || null,
    deviceType: String(raw?.deviceType ?? raw?.type ?? raw?.model ?? "").trim() || null,
    protocol: String(raw?.protocol ?? raw?.protocolType ?? "").trim() || null,
    lastPositionAt,
    rawPayload: raw,
  };
}

function normalizePosition(raw, deviceMap = new Map()) {
  const source = raw?.position && typeof raw.position === "object" ? raw.position : raw;
  const externalDeviceId = String(
    source?.deviceId ?? source?.device_id ?? raw?.deviceId ?? raw?.device_id ?? ""
  ).trim();
  const deviceRecord = externalDeviceId ? deviceMap.get(externalDeviceId) : null;
  const imei = String(
    source?.imei ??
      source?.IMEI ??
      raw?.imei ??
      raw?.IMEI ??
      deviceRecord?.imei ??
      ""
  ).trim();

  const latitude = Number(source?.latitude ?? source?.lat ?? source?.y);
  const longitude = Number(source?.longitude ?? source?.lng ?? source?.lon ?? source?.x);
  if (!imei || Number.isNaN(latitude) || Number.isNaN(longitude)) {
    return null;
  }

  const positionTime = normalizeDateTime(
    source?.timestamp ??
      source?.time ??
      source?.deviceTime ??
      source?.fixTime ??
      raw?.timestamp ??
      raw?.time ??
      null
  );

  return {
    externalPositionId: String(
      source?.positionId ??
        source?.id ??
        raw?.positionId ??
        raw?.id ??
        ""
    ).trim() || null,
    externalDeviceId: externalDeviceId || null,
    imei,
    latitude,
    longitude,
    speedKmh: Number(source?.speed ?? source?.speedKmh ?? source?.speed_kmh ?? 0) || 0,
    heading: Number(source?.heading ?? source?.course ?? 0) || 0,
    altitudeM: Number(source?.altitude ?? source?.alt ?? 0) || 0,
    positionTime: positionTime || new Date(),
    rawPayload: raw,
  };
}

function extractDistanceKm(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const checkNumeric = (value) => {
    const converted = Number(value);
    return Number.isNaN(converted) ? null : converted;
  };

  const candidateValues = [
    payload.distance,
    payload.totalDistance,
    payload.distanceKm,
    payload.total_distance,
    payload.km,
    payload?.data?.distance,
    payload?.data?.totalDistance,
    payload?.data?.distanceKm,
    payload?.result?.distance,
    payload?.result?.totalDistance,
  ];

  for (const value of candidateValues) {
    const numeric = checkNumeric(value);
    if (numeric !== null) {
      return numeric;
    }
  }
  return null;
}

module.exports = {
  extractDataArray,
  extractToken,
  normalizeDateTime,
  normalizeDevice,
  normalizePosition,
  extractDistanceKm,
};
