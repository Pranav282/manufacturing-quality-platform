CREATE OR REPLACE VIEW overall_quality_metrics AS
SELECT
    COUNT(*) AS parts_processed,
    SUM(response) AS failed_parts,
    SUM(response) * 1.0 / COUNT(*) AS failure_rate
FROM parts;

CREATE OR REPLACE VIEW station_exposure_metrics AS
WITH station_counts AS (
    SELECT
        v.station,
        COUNT(*) AS parts_observed,
        SUM(p.response) AS failed_parts
    FROM station_visits v
    JOIN parts p ON p.part_id = v.part_id
    GROUP BY v.station
)
SELECT
    s.station,
    s.parts_observed,
    s.failed_parts,
    s.failed_parts * 1.0 / s.parts_observed AS failure_rate,
    o.failure_rate AS overall_failure_rate,
    (s.failed_parts * 1.0 / s.parts_observed)
        / NULLIF(o.failure_rate, 0) AS rate_vs_overall,
    CASE
        WHEN s.parts_observed >= 1000 AND s.failed_parts >= 20
        THEN 'sufficient_for_initial_review'
        ELSE 'limited_sample'
    END AS review_status
FROM station_counts s
CROSS JOIN overall_quality_metrics o;