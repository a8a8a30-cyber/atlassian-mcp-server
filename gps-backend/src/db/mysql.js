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
  try {
    const rows = await query("SELECT 1 AS ok");
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
