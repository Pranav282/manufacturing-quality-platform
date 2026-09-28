SELECT
    station,
    COUNT(*) AS measurements,
    COUNT(DISTINCT feature_name) AS features,
    COUNT(DISTINCT part_id) AS parts
FROM mapped_measurements
WHERE station = 'L3_S32'
GROUP BY station;