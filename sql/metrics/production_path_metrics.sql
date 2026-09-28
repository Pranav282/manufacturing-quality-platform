CREATE OR REPLACE VIEW production_path_metrics AS
WITH part_lines AS (
    SELECT
        p.part_id,
        p.response,
        MAX(CASE WHEN v.station LIKE 'L0_S%' THEN 1 ELSE 0 END) AS l0,
        MAX(CASE WHEN v.station LIKE 'L1_S%' THEN 1 ELSE 0 END) AS l1,
        MAX(CASE WHEN v.station LIKE 'L2_S%' THEN 1 ELSE 0 END) AS l2,
        MAX(CASE WHEN v.station LIKE 'L3_S%' THEN 1 ELSE 0 END) AS l3
    FROM parts p
    LEFT JOIN station_visits v ON p.part_id = v.part_id
    GROUP BY p.part_id, p.response
),
labeled AS (
    SELECT
        response,
        CASE
            WHEN l0 + l1 + l2 + l3 = 0 THEN 'No recorded visits'
            ELSE TRIM(
                CONCAT(
                    CASE WHEN l0 = 1 THEN 'L0 ' ELSE '' END,
                    CASE WHEN l1 = 1 THEN 'L1 ' ELSE '' END,
                    CASE WHEN l2 = 1 THEN 'L2 ' ELSE '' END,
                    CASE WHEN l3 = 1 THEN 'L3 ' ELSE '' END
                )
            )
        END AS line_group
    FROM part_lines
)
SELECT
    line_group,
    COUNT(*) AS parts,
    SUM(response) AS failed_parts,
    ROUND(100.0 * SUM(response) / COUNT(*), 3) AS failure_pct
FROM labeled
GROUP BY line_group;