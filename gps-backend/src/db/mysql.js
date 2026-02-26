const mysql = require("mysql2/promise");
const { env } = require("../config/env");
const { logger } = require("../lib/logger");

let pool;

function getPool() {
  if (!pool) {
    pool = mysql.createPool({
      host: env.mysql.host,
      port: env.mysql.port,
      database: env.mysql.database,
      user: env.mysql.user,
      password: env.mysql.password,
      connectionLimit: env.mysql.connectionLimit,
      connectTimeout: env.mysql.connectTimeoutMs,
      waitForConnections: true,
      queueLimit: 0,
      timezone: "Z",
      namedPlaceholders: true,
    });
  }
  return pool;
}

async function query(sql, params = {}) {
  const [rows] = await getPool().execute(sql, params);
  return rows;
}

async function transaction(handler) {
  const connection = await getPool().getConnection();
  try {
    await connection.beginTransaction();
    const output = await handler(connection);
    await connection.commit();
    return output;
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

async function healthCheck() {
  const timeoutMs = Math.max(2000, env.mysql.connectTimeoutMs);
  try {
    const rows = await Promise.race([
      query("SELECT 1 AS ok"),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error("MySQL health check timeout")), timeoutMs)
      ),
    ]);
    return rows?.[0]?.ok === 1;
  } catch (error) {
    logger.error("MySQL health check failed", { error: error.message });
    return false;
  }
}

module.exports = {
  getPool,
  query,
  transaction,
  healthCheck,
};
