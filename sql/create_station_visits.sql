CREATE TABLE IF NOT EXISTS station_visits (
    part_id BIGINT NOT NULL,
    station VARCHAR NOT NULL,
    first_observed_time DOUBLE,
    last_observed_time DOUBLE,
    PRIMARY KEY (part_id, station)
);