-- SwaraSetu initial schema (PostgreSQL 15).
-- SQLAlchemy also creates tables at startup; this script provisions the
-- database ahead of time inside docker-compose for clean first boot.

CREATE TABLE IF NOT EXISTS phcs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    district VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL DEFAULT 'Bihar',
    facility_type VARCHAR(50) NOT NULL DEFAULT 'PHC',
    phone VARCHAR(20) NOT NULL DEFAULT '108',
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    is_24x7 BOOLEAN NOT NULL DEFAULT FALSE,
    doctor_available BOOLEAN NOT NULL DEFAULT FALSE,
    hours VARCHAR(60) NOT NULL DEFAULT '9 AM - 5 PM'
);

CREATE INDEX IF NOT EXISTS ix_phcs_district ON phcs (district);
CREATE INDEX IF NOT EXISTS ix_phcs_name ON phcs (name);

CREATE TABLE IF NOT EXISTS asha_assignments (
    id SERIAL PRIMARY KEY,
    asha_name VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    village VARCHAR(120) NOT NULL,
    district VARCHAR(100) NOT NULL,
    phc_id INTEGER REFERENCES phcs(id)
);

CREATE INDEX IF NOT EXISTS ix_asha_district ON asha_assignments (district);

CREATE TABLE IF NOT EXISTS cases (
    id SERIAL PRIMARY KEY,
    client_uuid VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    age_group VARCHAR(20) NOT NULL DEFAULT 'child',
    language VARCHAR(10) NOT NULL DEFAULT 'en',
    district VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    risk_score INTEGER NOT NULL,
    primary_cluster VARCHAR(30) NOT NULL,
    rationale_en TEXT NOT NULL DEFAULT '',
    rationale_keys TEXT NOT NULL DEFAULT '[]',
    actions_json TEXT NOT NULL DEFAULT '[]',
    red_flags_json TEXT NOT NULL DEFAULT '[]',
    source VARCHAR(20) NOT NULL DEFAULT 'online'
);

CREATE INDEX IF NOT EXISTS ix_cases_risk ON cases (risk_score);
CREATE INDEX IF NOT EXISTS ix_cases_district ON cases (district);
