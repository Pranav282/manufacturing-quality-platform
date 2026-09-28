CREATE TABLE IF NOT EXISTS parts (
    part_id BIGINT PRIMARY KEY,
    response TINYINT NOT NULL CHECK (response IN (0, 1))
);