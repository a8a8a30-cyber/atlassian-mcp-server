const fs = require("node:fs/promises");
const path = require("node:path");
const { getPool } = require("./mysql");
const { logger } = require("../lib/logger");

function splitSqlStatements(sqlScript) {
  return sqlScript
    .split(/;\s*\n/g)
    .map((statement) => statement.trim())
    .filter((statement) => statement.length > 0);
}

async function initSchema() {
  const schemaPath = path.resolve(process.cwd(), "sql", "schema.sql");
  const sqlScript = await fs.readFile(schemaPath, "utf-8");
  const statements = splitSqlStatements(sqlScript);
  const pool = getPool();

  for (const statement of statements) {
    await pool.query(statement);
  }

  logger.info("MySQL schema initialized", { statements: statements.length });
}

module.exports = { initSchema };
