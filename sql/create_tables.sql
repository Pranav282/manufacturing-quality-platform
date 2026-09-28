CREATE TABLE IF NOT EXISTS parts (
    part_id BIGINT PRIMARY KEY,
    response TINYINT NOT NULL CHECK (response IN (0, 1))
);

CREATE TABLE IF NOT EXISTS station_visits (
    part_id BIGINT NOT NULL,
    station VARCHAR NOT NULL,
    first_observed_time DOUBLE,
    last_observed_time DOUBLE,
    PRIMARY KEY (part_id, station)
);