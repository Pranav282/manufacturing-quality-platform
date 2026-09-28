SELECT
    COUNT(*) AS measurements,
    COUNT(DISTINCT feature_name) AS features,
    COUNT(*) FILTER (WHERE observed_time IS NULL) AS missing_times
FROM mapped_measurements;