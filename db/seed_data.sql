-- Mock data exercising all 6 in-scope use cases:
-- pending orders, picker location/task, shipment status, tote requirements,
-- PD completion estimate, SPD/FedEx cutoff estimate.
-- (For local testing, tests/conftest.py seeds an equivalent in-memory SQLite dataset
--  programmatically, since BigQuery DDL/DML syntax isn't portable to SQLite.)

INSERT INTO `${project}.${dataset}.users` (user_id, name, current_zone, current_task_id, status) VALUES
('U123', 'Alex Rivera', 'Zone-A', 'T1', 'active'),
('U124', 'Sam Chen', NULL, NULL, 'idle');

INSERT INTO `${project}.${dataset}.shipments` (shipment_id, ship_type, carrier, cutoff_time, status) VALUES
('SHP789', 'PD', NULL, TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 4 HOUR), 'in_progress'),
('SHP800', 'SPD', 'FedEx', TIMESTAMP_ADD(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR), 'in_progress');

INSERT INTO `${project}.${dataset}.orders` (order_id, shipment_id, status, priority, workstream, waved, created_at) VALUES
('O1', 'SHP789', 'pending', 'high', 'wave1', TRUE, CURRENT_TIMESTAMP()),
('O2', 'SHP789', 'pending', 'normal', 'wave1', FALSE, CURRENT_TIMESTAMP()),
('O3', 'SHP789', 'processed', 'normal', 'wave2', TRUE, CURRENT_TIMESTAMP());

INSERT INTO `${project}.${dataset}.tasks` (task_id, shipment_id, user_id, task_type, status, assigned_at, completed_at) VALUES
('T1', 'SHP789', 'U123', 'pick', 'pending', CURRENT_TIMESTAMP(), NULL),
('T2', 'SHP789', 'U123', 'pick', 'completed', TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 MINUTE), TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 MINUTE)),
('T3', 'SHP800', 'U123', 'pick', 'pending', CURRENT_TIMESTAMP(), NULL),
('T4', 'SHP800', 'U123', 'pick', 'completed', TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 20 MINUTE), TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 5 MINUTE));

INSERT INTO `${project}.${dataset}.totes` (tote_id, shipment_id, status) VALUES
('TT1', 'SHP789', 'required'),
('TT2', 'SHP789', 'completed'),
('TT3', 'SHP789', 'required');
