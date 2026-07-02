-- Nova PostgreSQL Schema v2
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS inventory;
CREATE SCHEMA IF NOT EXISTS sales;
CREATE SCHEMA IF NOT EXISTS hr;
-- Base table template
CREATE TABLE IF NOT EXISTS core.companies(
 id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 code text UNIQUE NOT NULL,
 name text NOT NULL,
 created_at timestamptz default now(),
 updated_at timestamptz default now(),
 is_deleted boolean default false
);
