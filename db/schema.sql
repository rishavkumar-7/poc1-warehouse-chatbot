-- Mock Manhattan WM schema for POC1 (BigQuery Standard SQL).
-- These field names are the contract every tool/estimation function relies on.

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.users` (
    user_id STRING,
    name STRING,
    current_zone STRING,
    current_task_id STRING,      -- NULL if idle
    status STRING                -- 'active' | 'idle'
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.shipments` (
    shipment_id STRING,
    ship_type STRING,            -- 'PD' | 'SPD'
    carrier STRING,               -- e.g. 'FedEx'; NULL for non-SPD shipments
    cutoff_time TIMESTAMP,
    status STRING                 -- 'in_progress' | 'complete'
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.orders` (
    order_id STRING,
    shipment_id STRING,
    status STRING,                 -- 'pending' | 'processed'
    priority STRING,               -- 'high' | 'normal' | 'low'
    workstream STRING,
    waved BOOL,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.tasks` (
    task_id STRING,
    shipment_id STRING,
    user_id STRING,
    task_type STRING,             -- 'pick' | 'pack' | etc.
    status STRING,                -- 'pending' | 'completed'
    assigned_at TIMESTAMP,
    completed_at TIMESTAMP        -- NULL until done
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.totes` (
    tote_id STRING,
    shipment_id STRING,
    status STRING                 -- 'required' | 'picked' | 'completed'
);
