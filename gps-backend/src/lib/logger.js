function log(level, message, metadata = undefined) {
  const payload = {
    level,
    message,
    timestamp: new Date().toISOString(),
  };
  if (metadata !== undefined) {
    payload.metadata = metadata;
  }
  // JSON logs simplify parsing in hosting platforms.
  // eslint-disable-next-line no-console
  console.log(JSON.stringify(payload));
}

const logger = {
  info(message, metadata) {
    log("info", message, metadata);
  },
  warn(message, metadata) {
    log("warn", message, metadata);
  },
  error(message, metadata) {
    log("error", message, metadata);
  },
};

module.exports = { logger };
