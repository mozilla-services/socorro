BEGIN;

-- Drop and recreate all views
DROP VIEW IF EXISTS bloat CASCADE;
DROP VIEW IF EXISTS crashes_by_user_build_view CASCADE;
DROP VIEW IF EXISTS crashes_by_user_rollup CASCADE;
DROP VIEW IF EXISTS crashes_by_user_view CASCADE;
DROP VIEW IF EXISTS current_server_status CASCADE;
DROP VIEW IF EXISTS product_info CASCADE;
DROP VIEW IF EXISTS default_versions CASCADE;
DROP VIEW IF EXISTS default_versions_builds CASCADE;
DROP VIEW IF EXISTS hang_report CASCADE;
DROP VIEW IF EXISTS home_page_graph_build_view CASCADE;
DROP VIEW IF EXISTS home_page_graph_view CASCADE;
DROP VIEW IF EXISTS performance_check_1 CASCADE;
DROP VIEW IF EXISTS pg_stat_statements CASCADE;
DROP VIEW IF EXISTS product_crash_ratio CASCADE;
DROP VIEW IF EXISTS product_os_crash_ratio CASCADE;
DROP VIEW IF EXISTS product_selector CASCADE;

CREATE VIEW bloat AS
    SELECT sml.schemaname, sml.tablename, (sml.reltuples)::bigint AS reltuples, (sml.relpages)::bigint AS relpages, sml.otta, round(CASE WHEN (sml.otta = (0)::double precision) THEN 0.0 ELSE ((sml.relpages)::numeric / (sml.otta)::numeric) END, 1) AS tbloat, (((sml.relpages)::bigint)::double precision - sml.otta) AS wastedpages, (sml.bs * ((((sml.relpages)::double precision - sml.otta))::bigint)::numeric) AS wastedbytes, pg_size_pretty((((sml.bs)::double precision * ((sml.relpages)::double precision - sml.otta)))::bigint) AS wastedsize, sml.iname, (sml.ituples)::bigint AS ituples, (sml.ipages)::bigint AS ipages, sml.iotta, round(CASE WHEN ((sml.iotta = (0)::double precision) OR (sml.ipages = 0)) THEN 0.0 ELSE ((sml.ipages)::numeric / (sml.iotta)::numeric) END, 1) AS ibloat, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE (((sml.ipages)::bigint)::double precision - sml.iotta) END AS wastedipages, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE ((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)) END AS wastedibytes, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN pg_size_pretty((0)::bigint) ELSE pg_size_pretty((((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)))::bigint) END AS wastedisize FROM (SELECT rs.schemaname, rs.tablename, cc.reltuples, cc.relpages, rs.bs, ceil(((cc.reltuples * (((((rs.datahdr + (rs.ma)::numeric) - CASE WHEN ((rs.datahdr % (rs.ma)::numeric) = (0)::numeric) THEN (rs.ma)::numeric ELSE (rs.datahdr % (rs.ma)::numeric) END))::double precision + rs.nullhdr2) + (4)::double precision)) / ((rs.bs)::double precision - (20)::double precision))) AS otta, COALESCE(c2.relname, '?'::name) AS iname, COALESCE(c2.reltuples, (0)::real) AS ituples, COALESCE(c2.relpages, 0) AS ipages, COALESCE(ceil(((c2.reltuples * ((rs.datahdr - (12)::numeric))::double precision) / ((rs.bs)::double precision - (20)::double precision))), (0)::double precision) AS iotta FROM (((((SELECT foo.ma, foo.bs, foo.schemaname, foo.tablename, ((foo.datawidth + (((foo.hdr + foo.ma) - CASE WHEN ((foo.hdr % foo.ma) = 0) THEN foo.ma ELSE (foo.hdr % foo.ma) END))::double precision))::numeric AS datahdr, (foo.maxfracsum * (((foo.nullhdr + foo.ma) - CASE WHEN ((foo.nullhdr % (foo.ma)::bigint) = 0) THEN (foo.ma)::bigint ELSE (foo.nullhdr % (foo.ma)::bigint) END))::double precision) AS nullhdr2 FROM (SELECT s.schemaname, s.tablename, constants.hdr, constants.ma, constants.bs, sum((((1)::double precision - s.null_frac) * (s.avg_width)::double precision)) AS datawidth, max(s.null_frac) AS maxfracsum, (constants.hdr + (SELECT (1 + (count(*) / 8)) FROM pg_stats s2 WHERE (((s2.null_frac <> (0)::double precision) AND (s2.schemaname = s.schemaname)) AND (s2.tablename = s.tablename)))) AS nullhdr FROM pg_stats s, (SELECT (SELECT (current_setting('block_size'::text))::numeric AS current_setting) AS bs, CASE WHEN ("substring"(foo.v, 12, 3) = ANY (ARRAY['8.0'::text, '8.1'::text, '8.2'::text])) THEN 27 ELSE 23 END AS hdr, CASE WHEN (foo.v ~ 'mingw32'::text) THEN 8 ELSE 4 END AS ma FROM (SELECT version() AS v) foo) constants GROUP BY s.schemaname, s.tablename, constants.hdr, constants.ma, constants.bs) foo) rs JOIN pg_class cc ON ((cc.relname = rs.tablename))) JOIN pg_namespace nn ON (((cc.relnamespace = nn.oid) AND (nn.nspname = rs.schemaname)))) LEFT JOIN pg_index i ON ((i.indrelid = cc.oid))) LEFT JOIN pg_class c2 ON ((c2.oid = i.indexrelid)))) sml WHERE ((((sml.relpages)::double precision - sml.otta) > (0)::double precision) OR (((sml.ipages)::double precision - sml.iotta) > (10)::double precision)) ORDER BY (sml.bs * ((((sml.relpages)::double precision - sml.otta))::bigint)::numeric) DESC, CASE WHEN ((sml.ipages)::double precision < sml.iotta) THEN (0)::double precision ELSE ((sml.bs)::double precision * ((sml.ipages)::double precision - sml.iotta)) END DESC;
ALTER TABLE public.bloat OWNER TO postgres;

CREATE VIEW crashes_by_user_build_view AS
    SELECT crashes_by_user_build.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user_build.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user_build.build_date, sum(crashes_by_user_build.report_count) AS report_count, sum(((crashes_by_user_build.report_count)::numeric / product_release_channels.throttle)) AS adjusted_report_count, sum(crashes_by_user_build.adu) AS adu, product_release_channels.throttle FROM ((((crashes_by_user_build JOIN product_versions USING (product_version_id)) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) JOIN os_names USING (os_short_name)) JOIN crash_types USING (crash_type_id)) GROUP BY crashes_by_user_build.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user_build.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user_build.build_date, product_release_channels.throttle;
ALTER TABLE public.crashes_by_user_build_view OWNER TO breakpad_rw;

CREATE VIEW crashes_by_user_rollup AS
    SELECT crashes_by_user.product_version_id, crashes_by_user.report_date, crashes_by_user.os_short_name, sum(crashes_by_user.report_count) AS report_count, min(crashes_by_user.adu) AS adu FROM (crashes_by_user JOIN crash_types USING (crash_type_id)) WHERE crash_types.include_agg GROUP BY crashes_by_user.product_version_id, crashes_by_user.report_date, crashes_by_user.os_short_name;
ALTER TABLE public.crashes_by_user_rollup OWNER TO postgres;

CREATE VIEW crashes_by_user_view AS
    SELECT crashes_by_user.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user.report_date, crashes_by_user.report_count, ((crashes_by_user.report_count)::numeric / product_release_channels.throttle) AS adjusted_report_count, crashes_by_user.adu, product_release_channels.throttle FROM ((((crashes_by_user JOIN product_versions USING (product_version_id)) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) JOIN os_names USING (os_short_name)) JOIN crash_types USING (crash_type_id));
ALTER TABLE public.crashes_by_user_view OWNER TO breakpad_rw;

CREATE VIEW current_server_status AS
    SELECT server_status.date_recently_completed, server_status.date_oldest_job_queued, date_part('epoch'::text, (server_status.date_created - server_status.date_oldest_job_queued)) AS oldest_job_age, server_status.avg_process_sec, server_status.avg_wait_sec, server_status.waiting_job_count, server_status.processors_count, server_status.date_created FROM server_status ORDER BY server_status.date_created DESC LIMIT 1;
ALTER TABLE public.current_server_status OWNER TO breakpad_rw;

CREATE VIEW product_info AS
    SELECT product_versions.product_version_id, product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.build_date AS start_date, product_versions.sunset_date AS end_date, product_versions.featured_version AS is_featured, product_versions.build_type, ((product_release_channels.throttle * (100)::numeric))::numeric(5,2) AS throttle, product_versions.version_sort, products.sort AS product_sort, release_channels.sort AS channel_sort, product_versions.has_builds, product_versions.is_rapid_beta FROM (((product_versions JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) JOIN products ON ((product_versions.product_name = products.product_name))) JOIN release_channels ON ((product_versions.build_type = release_channels.release_channel))) ORDER BY product_versions.product_name, product_versions.version_string;
ALTER TABLE public.product_info OWNER TO breakpad_rw;

CREATE VIEW default_versions AS
    SELECT count_versions.product_name, count_versions.version_string, count_versions.product_version_id FROM (SELECT product_info.product_name, product_info.version_string, product_info.product_version_id, row_number() OVER (PARTITION BY product_info.product_name ORDER BY ((('now'::text)::date >= product_info.start_date) AND (('now'::text)::date <= product_info.end_date)) DESC, product_info.is_featured DESC, product_info.channel_sort DESC) AS sort_count FROM product_info) count_versions WHERE (count_versions.sort_count = 1);
ALTER TABLE public.default_versions OWNER TO breakpad_rw;

CREATE VIEW default_versions_builds AS
    SELECT count_versions.product_name, count_versions.version_string, count_versions.product_version_id FROM (SELECT product_info.product_name, product_info.version_string, product_info.product_version_id, row_number() OVER (PARTITION BY product_info.product_name ORDER BY ((('now'::text)::date >= product_info.start_date) AND (('now'::text)::date <= product_info.end_date)) DESC, product_info.is_featured DESC, product_info.channel_sort DESC) AS sort_count FROM product_info WHERE product_info.has_builds) count_versions WHERE (count_versions.sort_count = 1);
ALTER TABLE public.default_versions_builds OWNER TO postgres;

CREATE VIEW hang_report AS
    SELECT product_versions.product_name AS product, product_versions.version_string AS version, browser_signatures.signature AS browser_signature, plugin_signatures.signature AS plugin_signature, daily_hangs.hang_id AS browser_hangid, flash_versions.flash_version, daily_hangs.url, daily_hangs.uuid, daily_hangs.duplicates, daily_hangs.report_date AS report_day FROM ((((daily_hangs JOIN product_versions USING (product_version_id)) JOIN signatures browser_signatures ON ((daily_hangs.browser_signature_id = browser_signatures.signature_id))) JOIN signatures plugin_signatures ON ((daily_hangs.plugin_signature_id = plugin_signatures.signature_id))) LEFT JOIN flash_versions USING (flash_version_id));
ALTER TABLE public.hang_report OWNER TO breakpad_rw;

CREATE VIEW home_page_graph_build_view AS
    SELECT home_page_graph_build.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph_build.build_date, sum(home_page_graph_build.report_count) AS report_count, sum(home_page_graph_build.adu) AS adu, crash_hadu(sum(home_page_graph_build.report_count), sum(home_page_graph_build.adu), product_release_channels.throttle) AS crash_hadu FROM ((home_page_graph_build JOIN product_versions USING (product_version_id)) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) GROUP BY home_page_graph_build.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph_build.build_date, product_release_channels.throttle;
ALTER TABLE public.home_page_graph_build_view OWNER TO breakpad_rw;

CREATE VIEW home_page_graph_view AS
    SELECT home_page_graph.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph.report_date, home_page_graph.report_count, home_page_graph.adu, home_page_graph.crash_hadu FROM (home_page_graph JOIN product_versions USING (product_version_id));
ALTER TABLE public.home_page_graph_view OWNER TO breakpad_rw;

CREATE VIEW performance_check_1 AS
    SELECT sum(tcbs.report_count) AS sum FROM tcbs WHERE ((tcbs.report_date >= (('now'::text)::date - 7)) AND (tcbs.report_date <= ('now'::text)::date));
ALTER TABLE public.performance_check_1 OWNER TO ganglia;

CREATE VIEW pg_stat_statements AS
    SELECT pg_stat_statements.userid, pg_stat_statements.dbid, pg_stat_statements.query, pg_stat_statements.calls, pg_stat_statements.total_time, pg_stat_statements.rows, pg_stat_statements.shared_blks_hit, pg_stat_statements.shared_blks_read, pg_stat_statements.shared_blks_written, pg_stat_statements.local_blks_hit, pg_stat_statements.local_blks_read, pg_stat_statements.local_blks_written, pg_stat_statements.temp_blks_read, pg_stat_statements.temp_blks_written FROM pg_stat_statements() pg_stat_statements(userid, dbid, query, calls, total_time, rows, shared_blks_hit, shared_blks_read, shared_blks_written, local_blks_hit, local_blks_read, local_blks_written, temp_blks_read, temp_blks_written);
ALTER TABLE public.pg_stat_statements OWNER TO postgres;

CREATE VIEW product_crash_ratio AS
    SELECT crcounts.product_version_id, product_versions.product_name, product_versions.version_string, crcounts.report_date AS adu_date, (sum(crcounts.report_count))::bigint AS crashes, sum(crcounts.adu) AS adu_count, (product_release_channels.throttle)::numeric(5,2) AS throttle, (sum(((crcounts.report_count)::numeric / product_release_channels.throttle)))::integer AS adjusted_crashes, crash_hadu((sum(crcounts.report_count))::bigint, sum(crcounts.adu), product_release_channels.throttle) AS crash_ratio FROM ((crashes_by_user_rollup crcounts JOIN product_versions ON ((crcounts.product_version_id = product_versions.product_version_id))) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) GROUP BY crcounts.product_version_id, product_versions.product_name, product_versions.version_string, crcounts.report_date, product_release_channels.throttle;
ALTER TABLE public.product_crash_ratio OWNER TO breakpad_rw;

CREATE VIEW product_os_crash_ratio AS
    SELECT crcounts.product_version_id, product_versions.product_name, product_versions.version_string, os_names.os_short_name, os_names.os_name, crcounts.report_date AS adu_date, (sum(crcounts.report_count))::bigint AS crashes, sum(crcounts.adu) AS adu_count, (product_release_channels.throttle)::numeric(5,2) AS throttle, (sum(((crcounts.report_count)::numeric / product_release_channels.throttle)))::integer AS adjusted_crashes, crash_hadu((sum(crcounts.report_count))::bigint, sum(crcounts.adu), product_release_channels.throttle) AS crash_ratio FROM (((crashes_by_user_rollup crcounts JOIN product_versions ON ((crcounts.product_version_id = product_versions.product_version_id))) JOIN os_names ON ((crcounts.os_short_name = os_names.os_short_name))) JOIN product_release_channels ON (((product_versions.product_name = product_release_channels.product_name) AND (product_versions.build_type = product_release_channels.release_channel)))) GROUP BY crcounts.product_version_id, product_versions.product_name, product_versions.version_string, os_names.os_name, os_names.os_short_name, crcounts.report_date, product_release_channels.throttle;
ALTER TABLE public.product_os_crash_ratio OWNER TO breakpad_rw;

CREATE VIEW product_selector AS
    SELECT product_versions.product_name, product_versions.version_string, 'new'::text AS which_table, product_versions.version_sort, product_versions.has_builds, product_versions.is_rapid_beta FROM product_versions WHERE (now() <= product_versions.sunset_date) ORDER BY product_versions.product_name, product_versions.version_string;
ALTER TABLE public.product_selector OWNER TO breakpad_rw;

COMMIT;



