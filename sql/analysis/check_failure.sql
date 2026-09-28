WITH line3_parts AS (
    SELECT DISTINCT part_id
    FROM station_visits
    WHERE station LIKE 'L3_S%'
),
s32_parts AS (
    SELECT part_id
    FROM station_visits
    WHERE station = 'L3_S32'
)
SELECT
    CASE
        WHEN s.part_id IS NOT NULL THEN 'L3_S32 observed'
        ELSE 'Other L3 parts'
    END AS part_group,
    COUNT(*) AS parts,
    SUM(p.response) AS failed_parts,
    ROUND(100.0 * SUM(p.response) / COUNT(*), 3) AS failure_pct
FROM line3_parts l
JOIN parts p ON p.part_id = l.part_id
LEFT JOIN s32_parts s ON s.part_id = l.part_id
GROUP BY 1
ORDER BY 1;