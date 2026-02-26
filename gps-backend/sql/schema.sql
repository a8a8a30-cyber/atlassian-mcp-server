CREATE TABLE IF NOT EXISTS rental_contracts (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  external_contract_id VARCHAR(120) NOT NULL UNIQUE,
  customer_name VARCHAR(160) NULL,
  vehicle_plate VARCHAR(40) NULL,
  device_imei VARCHAR(30) NOT NULL,
  start_at DATETIME NOT NULL,
  end_at DATETIME NULL,
  actual_end_at DATETIME NULL,
  speed_limit_kmh INT NOT NULL DEFAULT 120,
  distance_limit_km DECIMAL(10, 2) NOT NULL DEFAULT 500.00,
  status ENUM('active', 'closed', 'cancelled') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_contract_device_status (device_imei, status),
  INDEX idx_contract_start_end (start_at, end_at)
);

CREATE TABLE IF NOT EXISTS gps_devices (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  external_device_id VARCHAR(120) NOT NULL UNIQUE,
  imei VARCHAR(30) NOT NULL UNIQUE,
  name VARCHAR(160) NULL,
  device_type VARCHAR(80) NULL,
  protocol VARCHAR(60) NULL,
  last_position_at DATETIME NULL,
  raw_payload JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_devices_imei (imei),
  INDEX idx_devices_last_position (last_position_at)
);

CREATE TABLE IF NOT EXISTS gps_positions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  external_position_id VARCHAR(120) NULL,
  external_device_id VARCHAR(120) NULL,
  imei VARCHAR(30) NOT NULL,
  latitude DECIMAL(10, 7) NOT NULL,
  longitude DECIMAL(10, 7) NOT NULL,
  speed_kmh DECIMAL(10, 2) NOT NULL DEFAULT 0,
  heading DECIMAL(10, 2) NULL,
  altitude_m DECIMAL(10, 2) NULL,
  position_time DATETIME NOT NULL,
  received_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  raw_payload JSON NULL,
  UNIQUE KEY uniq_external_position (external_position_id),
  UNIQUE KEY uniq_position_fingerprint (imei, position_time, latitude, longitude),
  INDEX idx_positions_imei_time (imei, position_time),
  INDEX idx_positions_device_time (external_device_id, position_time)
);

CREATE TABLE IF NOT EXISTS contract_distance_snapshots (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  contract_id BIGINT NOT NULL,
  distance_km DECIMAL(12, 3) NOT NULL,
  source ENUM('gpsdome_summary', 'positions_fallback') NOT NULL,
  snapshot_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  details JSON NULL,
  INDEX idx_distance_contract_time (contract_id, snapshot_time),
  CONSTRAINT fk_distance_contract
    FOREIGN KEY (contract_id) REFERENCES rental_contracts(id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contract_alerts (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  contract_id BIGINT NULL,
  imei VARCHAR(30) NOT NULL,
  alert_type ENUM('speed', 'distance') NOT NULL,
  threshold_value DECIMAL(10, 2) NOT NULL,
  actual_value DECIMAL(10, 2) NOT NULL,
  message VARCHAR(255) NOT NULL,
  position_id BIGINT NULL,
  metadata JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  resolved_at DATETIME NULL,
  INDEX idx_alerts_contract_time (contract_id, created_at),
  INDEX idx_alerts_imei_type_time (imei, alert_type, created_at),
  CONSTRAINT fk_alert_contract
    FOREIGN KEY (contract_id) REFERENCES rental_contracts(id)
    ON DELETE SET NULL,
  CONSTRAINT fk_alert_position
    FOREIGN KEY (position_id) REFERENCES gps_positions(id)
    ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sync_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  job_name VARCHAR(80) NOT NULL,
  status ENUM('running', 'success', 'failed') NOT NULL DEFAULT 'running',
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at DATETIME NULL,
  message TEXT NULL,
  INDEX idx_sync_job_time (job_name, started_at)
);
