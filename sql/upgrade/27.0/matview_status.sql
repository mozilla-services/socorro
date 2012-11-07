BEGIN;

DROP TABLE IF EXISTS matview_runs;
DROP TABLE IF EXISTS matview_functions;

-- Let's restrict what gets logged into matview_runs
CREATE TABLE matview_functions (
    funcname TEXT UNIQUE NOT NULL
);

INSERT into matview_functions
    VALUES('check_raw_adu')
    , ('update_product_versions')
    , ('update_signatures')
    , ('update_os_versions')
    , ('update_tcbs')
    , ('update_adu')
    , ('update_hang_report')
    , ('update_rank_compare')
    , ('update_nightly_builds')
    , ('update_build_adu')
    , ('update_crashes_by_user')
    , ('update_crashes_by_user_build')
    , ('update_correlations')
    , ('update_home_page_graph')
    , ('update_home_page_graph_build')
    , ('update_tcbs_build')
    , ('update_explosiveness');

CREATE TABLE matview_runs (
    matview_function TEXT NOT NULL REFERENCES matview_functions(funcname),
    run_at TIMESTAMPTZ NOT NULL,
    run_duration INTERVAL NOT NULL,
    succeeded BOOLEAN NOT NULL
);

COMMIT;
