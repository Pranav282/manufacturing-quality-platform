WITH part_routes AS (
    SELECT
        part_id,
        MAX(CASE WHEN station LIKE 'L0_S%' THEN 1 ELSE 0 END) AS l0,
        MAX(CASE WHEN station LIKE 'L1_S%' THEN 1 ELSE 0 END) AS l1,
        MAX(CASE WHEN station LIKE 'L2_S%' THEN 1 ELSE 0 END) AS l2,
        MAX(CASE WHEN station LIKE 'L3_S%' THEN 1 ELSE 0 END) AS l3,
        MAX(CASE WHEN station = 'L3_S32' THEN 1 ELSE 0 END) AS visited_s32
    FROM station_visits
    GROUP BY part_id
),
grouped AS (
    SELECT
        p.response,
        r.visited_s32,
        TRIM(CONCAT(
            CASE WHEN r.l0 = 1 THEN 'L0 ' ELSE '' END,
            CASE WHEN r.l1 = 1 THEN 'L1 ' ELSE '' END,
            CASE WHEN r.l2 = 1 THEN 'L2 ' ELSE '' END,
            'L3'
        )) AS line_group
    FROM part_routes r
    JOIN parts p ON p.part_id = r.part_id
    WHERE r.l3 = 1
)
SELECT
    line_group,
    CASE WHEN visited_s32 = 1
         THEN 'L3_S32 observed'
         ELSE 'L3_S32 not observed'
    END AS s32_group,
    COUNT(*) AS parts,
    SUM(response) AS failed_parts,
    ROUND(100.0 * SUM(response) / COUNT(*), 3) AS failure_pct
FROM grouped
GROUP BY line_group, visited_s32
ORDER BY line_group, visited_s32 DESC;