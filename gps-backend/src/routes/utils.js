function asyncHandler(handler) {
  return (req, res, next) => {
    Promise.resolve(handler(req, res, next)).catch(next);
  };
}

function requiredFields(body, fieldNames = []) {
  const missing = [];
  for (const field of fieldNames) {
    if (
      body[field] === undefined ||
      body[field] === null ||
      String(body[field]).trim() === ""
    ) {
      missing.push(field);
    }
  }
  return missing;
}

module.exports = { asyncHandler, requiredFields };
