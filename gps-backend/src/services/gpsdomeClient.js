const axios = require("axios");
const { env } = require("../config/env");
const { logger } = require("../lib/logger");
const {
  extractDataArray,
  extractDistanceKm,
  extractToken,
} = require("../lib/normalizers");

class GpsDomeClient {
  constructor() {
    this.http = axios.create({
      baseURL: env.gpsdome.baseUrl,
      timeout: env.gpsdome.requestTimeoutMs,
    });
    this.session = {
      token: null,
      cookie: null,
      expiresAt: 0,
    };
  }

  hasValidSession() {
    return Date.now() < this.session.expiresAt && (this.session.token || this.session.cookie);
  }

  async authenticate(force = false) {
    if (!force && this.hasValidSession()) {
      return this.session;
    }

    if (!env.gpsdome.email || !env.gpsdome.password) {
      throw new Error("GPSDOME_EMAIL or GPSDOME_PASSWORD are not configured.");
    }

    const response = await this.http.post(env.gpsdome.sessionEndpoint, {
      email: env.gpsdome.email,
      password: env.gpsdome.password,
    });

    const token = extractToken(response.data);
    const rawCookies = response.headers?.["set-cookie"];
    const cookie = Array.isArray(rawCookies) ? rawCookies.join("; ") : null;

    this.session = {
      token: token || null,
      cookie: cookie || null,
      // Session validity can vary; this is a pragmatic cache window.
      expiresAt: Date.now() + 45 * 60 * 1000,
    };

    logger.info("Authenticated with GPSDome session", {
      tokenReceived: Boolean(token),
      cookieReceived: Boolean(cookie),
    });

    return this.session;
  }

  async getAuthHeaders() {
    if (env.gpsdome.useBasicAuth) {
      const basic = Buffer.from(
        `${env.gpsdome.email}:${env.gpsdome.password}`,
        "utf-8"
      ).toString("base64");
      return { Authorization: `Basic ${basic}` };
    }

    const session = await this.authenticate();
    const headers = {};
    if (session.token) {
      headers.Authorization = `Bearer ${session.token}`;
    }
    if (session.cookie) {
      headers.Cookie = session.cookie;
    }
    return headers;
  }

  async request(config, retry = true) {
    const headers = await this.getAuthHeaders();
    try {
      return await this.http.request({
        ...config,
        headers: {
          ...headers,
          ...(config.headers || {}),
        },
      });
    } catch (error) {
      const statusCode = error?.response?.status;
      if (retry && statusCode === 401) {
        logger.warn("GPSDome request unauthorized, re-authenticating");
        await this.authenticate(true);
        return this.request(config, false);
      }
      throw error;
    }
  }

  async getDevices() {
    const response = await this.request({
      method: "GET",
      url: env.gpsdome.devicesEndpoint,
    });
    return extractDataArray(response.data);
  }

  async getPositions(filters = {}) {
    const params = {};
    if (filters.from) params.from = filters.from;
    if (filters.to) params.to = filters.to;
    if (filters.deviceId) params.deviceId = filters.deviceId;
    if (filters.imei) params.imei = filters.imei;
    if (filters.limit) params.limit = filters.limit;

    const response = await this.request({
      method: "GET",
      url: env.gpsdome.positionsEndpoint,
      params,
    });
    return extractDataArray(response.data);
  }

  async getDistanceSummary(filters = {}) {
    const params = {};
    if (filters.from) params.from = filters.from;
    if (filters.to) params.to = filters.to;
    if (filters.deviceId) params.deviceId = filters.deviceId;
    if (filters.imei) params.imei = filters.imei;

    const response = await this.request({
      method: "GET",
      url: env.gpsdome.reportsSummaryEndpoint,
      params,
    });

    return {
      raw: response.data,
      distanceKm: extractDistanceKm(response.data),
    };
  }
}

module.exports = {
  GpsDomeClient,
};
