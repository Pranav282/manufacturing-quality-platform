import duckdb
import streamlit as st

DB = "data/processed/quality.duckdb"

st.set_page_config(page_title="Manufacturing Quality", layout="wide")
st.title("Manufacturing Quality")
st.caption("Bosch Production Line Performance · final quality outcomes")

@st.cache_data
def load_metrics():
    with duckdb.connect(DB, read_only=True) as con:
        overall = con.execute(
            "SELECT * FROM overall_quality_metrics"
        ).fetchdf()

        stations = con.execute("""
            SELECT station, parts_observed, failed_parts, failure_rate
            FROM station_exposure_metrics
            WHERE parts_observed >= 1000
            ORDER BY failure_rate DESC
        """).fetchdf()

        paths = con.execute("""
            SELECT *
            FROM production_path_metrics
            ORDER BY parts DESC
        """).fetchdf()

    return overall, stations, paths

overall, stations, paths = load_metrics()
row = overall.iloc[0]

a, b, c = st.columns(3)
a.metric("Parts processed", f"{int(row['parts_processed']):,}")
b.metric("Failed parts", f"{int(row['failed_parts']):,}")
c.metric("Final failure rate", f"{row['failure_rate']:.3%}")

st.subheader("Failure rate by recorded station")
st.caption("A station visit is an observed data record. Rates are associations with the final part outcome.")
st.bar_chart(
    stations.head(15).set_index("station")["failure_rate"] * 100,
    y_label="Failure rate (%)",
)
st.dataframe(stations, hide_index=True)

st.subheader("Recorded line combinations")
st.dataframe(paths, hide_index=True)

@st.cache_data
def load_s32_comparison():
    with duckdb.connect(DB, read_only=True) as con:
        return con.execute("""
            WITH l3_parts AS (
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
                CASE WHEN s.part_id IS NULL
                    THEN 'Other L3 parts'
                    ELSE 'L3_S32 observed'
                END AS part_group,
                COUNT(*) AS parts,
                SUM(p.response) AS failed_parts,
                ROUND(100.0 * SUM(p.response) / COUNT(*), 3)
                    AS failure_pct
            FROM l3_parts l
            JOIN parts p ON p.part_id = l.part_id
            LEFT JOIN s32_parts s ON s.part_id = l.part_id
            GROUP BY 1
            ORDER BY failure_pct DESC
        """).fetchdf()

st.subheader("Investigation: L3_S32")
st.write(
    "Parts observed at L3_S32 have a higher final failure rate "
    "than other parts observed on line L3."
)

s32 = load_s32_comparison()
st.bar_chart(
    s32.set_index("part_group")["failure_pct"],
    y_label="Final failure rate (%)",
)
st.dataframe(s32, hide_index=True)

st.caption(
    "This comparison is observational. Other recorded paths and "
    "production conditions may differ between the groups."
)

@st.cache_data
def load_s32_by_line_group():
    with duckdb.connect(DB, read_only=True) as con:
        return con.execute("""
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
            groups AS (
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
                    THEN 'S32 observed'
                    ELSE 'S32 not observed'
                END AS s32_group,
                COUNT(*) AS parts,
                SUM(response) AS failed_parts,
                ROUND(100.0 * SUM(response) / COUNT(*), 3)
                    AS failure_pct
            FROM groups
            GROUP BY line_group, visited_s32
            ORDER BY line_group, visited_s32 DESC
        """).fetchdf()

st.subheader("Comparison within recorded line groups")
st.dataframe(load_s32_by_line_group(), hide_index=True)
st.caption(
    "Compare S32 observed and not observed within the same line group. "
    "Small groups should be interpreted cautiously."
)

st.info(
    "The dataset does not identify where or when a part failed. "
    "Station differences do not establish causation."
)