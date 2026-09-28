CREATE TABLE IF NOT EXISTS measurements (
    part_id BIGINT NOT NULL,
    station VARCHAR NOT NULL,
    feature_name VARCHAR NOT NULL,
    measurement_value DOUBLE NOT NULL,
    date_feature_name VARCHAR,
    observed_time DOUBLE,
    PRIMARY KEY (part_id, feature_name)
);