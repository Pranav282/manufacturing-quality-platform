WITH l3_parts AS (
    SELECT
        part_id,
        MIN(first_observed_time) AS first_l3_time,
        MAX(CASE WHEN station = 'L3_S32' THEN 1 ELSE 0 END) AS visited_s32
    FROM station_visits
    WHERE station LIKE 'L3_S%'
    GROUP BY part_id
),
cohorts AS (
    SELECT
        part_id,
        visited_s32,
        NTILE(10) OVER (ORDER BY first_l3_time, part_id) AS time_cohort
    FROM l3_parts
    WHERE first_l3_time IS NOT NULL
)
SELECT
    c.time_cohort,
    CASE WHEN c.visited_s32 = 1
         THEN 'S32 observed'
         ELSE 'S32 not observed'
    END AS s32_group,
    COUNT(*) AS parts,
    SUM(p.response) AS failed_parts,
    ROUND(100.0 * SUM(p.response) / COUNT(*), 3) AS failure_pct
FROM cohorts c
JOIN parts p ON p.part_id = c.part_id
GROUP BY c.time_cohort, c.visited_s32
ORDER BY c.time_cohort, c.visited_s32 DESC;