\set ECHO
\set QUIET 1
-- Turn off echo and keep things quiet.

-- Format the output for nice TAP.
\pset format unaligned
\pset tuples_only true
\pset pager

-- Revert all changes on failure.
\set ON_ERROR_ROLLBACK 1
\set ON_ERROR_STOP true
\set QUIET 1

-- search path
SET search_path = pgtap,public;
SET timezone = 'UTC';

-- Load the TAP functions.
BEGIN;

-- Plan the tests.
SELECT plan(88);

-- Check that all new tables are present
SELECT has_table( 'build_adu', 'should have table build_adu');
SELECT has_table( 'crashes_by_user', 'should have table crash_by_user');
SELECT has_table( 'crashes_by_user_build', 'should have table crash_by_user_build');
SELECT has_table( 'home_page_graph', 'should have table home_page_graph');
SELECT has_table( 'home_page_graph_build', 'should have table home_page_graph_build');
SELECT has_table( 'product_adu', 'should have table product_adu');
SELECT has_table( 'tcbs', 'should have table tcbs');
SELECT has_table( 'tcbs_build', 'should have table tcbs_build');

-- check for new columns
SELECT has_column( 'products', 'rapid_beta_version', 'products has new column rapid_beta_version');
SELECT has_column( 'product_versions','has_builds','product_verions has new column has_builds');
SELECT has_column( 'product_versions','is_rapid_beta','product_verions has new column is_rapid_beta');
SELECT has_column( 'product_versions','rapid_beta_id','product_verions has new column rapid_beta_id');

-- check for dropped tables
SELECT hasnt_table(tabdropped, 'table ' || tabdropped || ' should no longer exist.')
FROM
UNNEST(ARRAY ['alexa_topsites','top_crashes_by_signature','top_crashes_by_url','top_crashes_by_url_signature','signature_build','signature_first','signature_bugs_rollup','signature_productdims','release_build_type_map', 'builds','osdims','product_version_sort','product_visibility','productdims','urldims','daily_crashes','daily_crash_codes']) as tabsdropped(tabdropped);

SELECT has_function(funcname, 'function ' || funcname || ' should exist.')
FROM
UNNEST(
ARRAY['backfill_tcbs_build','backfill_tcbs','update_build_adu','backfill_build_adu','update_crashes_by_user_build','backfill_crashes_by_user_build','update_crashes_by_user','backfill_crashes_by_user','update_home_page_graph','backfill_home_page_graph','update_home_page_graph_build','backfill_home_page_graph_build','reports_clean_done',
'crash_hadu','is_rapid_beta','update_adu','backfill_adu','update_product_versions','update_tcbs_build','update_tcbs']) as funcs(funcname);

-- check reports_clean_done
SELECT has_function('reports_clean_done', ARRAY['date','interval'], 'reports_clean_done should have check_period parameter');

-- check that all the views exist
SELECT has_view(vwname, 'view ' || vwname || ' should exist.')
FROM UNNEST (
ARRAY['product_info','product_selector','default_versions_builds','product_crash_ratio',
			'product_os_crash_ratio'] ) as vws(vwname);

--check that update_product_versions executes without error
SELECT lives_ok('SELECT update_product_versions();', 'update_product_versions should execute without error');

--check that update_reports_clean executes without error
SELECT lives_ok('SELECT update_reports_clean( now() + interval ''1 week'', now() + interval ''8 days'', false )',
	'update_reports_clean should execute without error')

-- check that all the update functions execute without errors

SELECT lives_ok ( 'SELECT ' || funcname || '( current_date + 30, false)', 'function ' || funcname || ' should execute without errors.' )
FROM UNNEST (
ARRAY['update_build_adu','update_crashes_by_user_build','update_crashes_by_user','update_home_page_graph','update_home_page_graph_build','update_adu','update_tcbs_build','update_tcbs']
) as funcs(funcname);

SELECT lives_ok ( 'SELECT ' || funcname || '( current_date + 30)', 'function ' || funcname || ' should execute without errors.' )
FROM UNNEST (
ARRAY['backfill_tcbs_build','backfill_tcbs','backfill_build_adu','backfill_crashes_by_user_build','backfill_crashes_by_user','backfill_home_page_graph','backfill_home_page_graph_build']
) as funcs(funcname);

--test tcbs_build
SELECT results_eq (
	$q$SELECT count(*) FROM reports WHERE product = 'WaterWolf'
		AND version = '4.0a1' AND date_processed BETWEEN '2012-07-01' and '2012-07-04'$q$,
	$q$SELECT sum(report_count) FROM tcbs_build
		WHERE product_version_id = (SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' AND version_string = '4.0a1')
		AND report_date BETWEEN '2012-07-01' AND '2012-07-03'$q$,
	'tcbs_build for Waterwolf 4.0a1 7/1 to 7/3 should match totals from reports');

SELECT results_eq (
	$q$SELECT count(*) FROM reports WHERE product = 'WaterWolf'
		AND version = '4.0a2' AND date_processed BETWEEN '2012-06-27' and '2012-07-04'
		AND os_name ILIKE 'win%'$q$,
	$q$SELECT sum(win_count) FROM tcbs_build
		WHERE product_version_id = (SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' AND version_string = '4.0a2')
		AND report_date BETWEEN '2012-06-27' AND '2012-07-03'$q$,
	'tcbs_build for Waterwolf 4.0a2 6/27 to 7/3 should match windows totals from reports');

--test build_adu

SELECT results_eq(
	$q$SELECT sum(adu_count) FROM raw_adu
		WHERE product_name = 'WaterWolf' AND product_version = '5.0a1'
		AND "date" BETWEEN '2012-06-29' and '2012-07-02'$q$,
	$q$SELECT sum(adu_count) FROM build_adu
	WHERE product_version_id = (SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' AND version_string = '5.0a1')
		AND adu_date BETWEEN '2012-06-29' AND '2012-07-02'$q$,
	'build_adu for Waterwolf 5.0a1 6/29 to 7/2 should match raw_adu totals.');

SELECT results_eq(
	$q$SELECT sum(adu_count) FROM raw_adu
		WHERE product_name = 'Nighttrain' AND product_version = '5.0a1'
		AND "date" BETWEEN '2012-06-28' and '2012-07-03'$q$,
	$q$SELECT sum(adu_count) FROM build_adu
	WHERE product_version_id = (SELECT product_version_id FROM product_versions
			WHERE product_name = 'Nighttrain' AND version_string = '4.0a2')
		AND adu_date BETWEEN '2012-06-28' AND '2012-07-03'$q$,
	'build_adu for Nighttrain 4.0a2 6/28 to 7/3 should match raw_adu totals.');

--test home_page_graph

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'WaterWolf' AND version = '2.0'
			AND ( process_type <> 'browser'
			OR hangid IS NULL )
			AND date_processed BETWEEN '2012-06-29' and '2012-06-30'$q$,
	$q$SELECT sum(report_count) FROM home_page_graph
		WHERE report_date = '2012-06-29'
		AND product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' and version_string = '2.0')$q$,
	'home_page_graph totals for 6/29 for WaterWolf 2.0 should match reports' );

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'Nighttrain' AND version = '2.1'
			AND ( process_type <> 'browser'
			OR hangid IS NULL )
			AND date_processed BETWEEN '2012-07-04' and '2012-07-05'$q$,
	$q$SELECT sum(report_count) FROM home_page_graph
		WHERE report_date = '2012-07-04'
		AND product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'Nighttrain' and version_string = '2.1')$q$,
	'home_page_graph totals for 7/4 for Nighttrain 2.1 should match reports' );

--test home_page_graph_build

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'WaterWolf' AND version = '5.0a1'
			AND ( process_type <> 'browser'
			OR hangid IS NULL )
			AND date_processed BETWEEN '2012-06-29' and '2012-06-30'$q$,
	$q$SELECT sum(report_count) FROM home_page_graph
		WHERE report_date = '2012-06-29'
		AND product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' and version_string = '5.0a1')$q$,
	'home_page_graph_build totals for 6/29 for WaterWolf 5.0a1 should match reports' );

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'Nighttrain' AND version = '4.0a2'
			AND ( process_type <> 'browser'
			OR hangid IS NULL )
			AND date_processed BETWEEN '2012-07-04' and '2012-07-05'$q$,
	$q$SELECT sum(report_count) FROM home_page_graph
		WHERE report_date = '2012-07-04'
		AND product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'Nighttrain' and version_string = '4.0a2')$q$,
	'home_page_graph_build totals for 7/4 for Nighttrain 4.0a2 should match reports' );

--test crashes_by_user

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'WaterWolf' AND version = '2.0'
			AND os_name LIKE 'Mac%'
			AND process_type = 'browser'
			AND hangid IS NULL
			AND date_processed BETWEEN '2012-06-29' and '2012-07-05'$q$,
	$q$SELECT sum(report_count) FROM crashes_by_user
	WHERE product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' and version_string = '2.0')
		AND crash_type_id IN (
			SELECT crash_type_id FROM crash_types
			WHERE crash_type = 'Browser')
		AND os_short_name = 'Mac'
		AND report_date BETWEEN '2012-06-29' and '2012-07-04'$q$,
	'crashes_by_user totals for Waterwolf 2.0, 6/29-7/5, Mac Browser crashes, should match reports' );

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'WaterWolf' AND version = '2.1'
			AND process_type = 'plugin'
			AND hangid IS NULL
			AND date_processed BETWEEN '2012-07-01' and '2012-07-07'$q$,
	$q$SELECT sum(report_count) FROM crashes_by_user
	WHERE product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' and version_string = '2.1')
		AND crash_type_id IN (
			SELECT crash_type_id FROM crash_types
			WHERE crash_type = 'OOP Plugin')
		AND report_date BETWEEN '2012-07-01' and '2012-07-06'$q$,
	'crashes_by_user totals for Waterwolf 2.1, 7/1-7/7, OOP crashes, should match reports' );

--test crashes_by_user_build

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'WaterWolf' AND version = '4.0a1'
			AND os_name LIKE 'Mac%'
			AND process_type = 'browser'
			AND hangid IS NULL
			AND date_processed BETWEEN '2012-06-29' and '2012-07-05'$q$,
	$q$SELECT sum(report_count) FROM crashes_by_user_build
	WHERE product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'WaterWolf' and version_string = '4.0a1')
		AND crash_type_id IN (
			SELECT crash_type_id FROM crash_types
			WHERE crash_type = 'Browser')
		AND os_short_name = 'Mac'
		AND report_date BETWEEN '2012-06-29' and '2012-07-04'$q$,
	'crashes_by_user_build totals for Waterwolf 4.0a1, 6/29-7/4, Mac Browser crashes, should match reports' );

SELECT results_eq(
	$q$SELECT count(*) FROM reports
		WHERE product = 'Waterwolf' AND version = '5.0a2'
			AND process_type = 'plugin'
			AND hangid IS NULL
			AND date_processed BETWEEN '2012-06-27' and '2012-07-04'$q$,
	$q$SELECT coalesce(sum(report_count),0) FROM crashes_by_user_build
	WHERE product_version_id IN (
			SELECT product_version_id FROM product_versions
			WHERE product_name = 'Waterwolf' and version_string = '5.0a2')
		AND crash_type_id IN (
			SELECT crash_type_id FROM crash_types
			WHERE crash_type = 'OOP Plugin')
		AND report_date BETWEEN '2012-06-27' and '2012-07-03'$q$,
	'crashes_by_user_build totals for Nighttrain 5.0a1, 6/27-7/3, OOP crashes, should match reports' );

-- test adding a new rapid beta

INSERT INTO releases_raw
VALUES ( 'WaterWolf', '4.0', 'Windows', '2012070500027', 'Beta', 1, 'beta' ),
	( 'WaterWolf', '4.0', 'Mac OS X', '2012070500027', 'Beta', 1, 'beta' ),
	( 'WaterWolf', '4.0', 'Linux', '2012070500027', 'Beta', 1, 'beta' ),
	( 'WaterWolf', '4.0', 'Windows', '2012070600027', 'Beta', 2, 'beta' ),
	( 'WaterWolf', '4.0', 'Mac OS X', '2012070600027', 'Beta', 2, 'beta' ),
	( 'WaterWolf', '4.0', 'Linux', '2012070600027', 'Beta', 2, 'beta' );

SELECT update_product_versions();

SELECT results_eq(
	$q$SELECT COUNT(*) FROM product_versions
		WHERE major_version = '4.0' and build_type = 'beta'$q$,
	$q$SELECT 3::bigint;$q$,
	'There should be 3 beta records for 4.0');

SELECT results_eq(
	$q$SELECT COUNT(*) FROM product_versions
		WHERE version_string = '4.0b' and is_rapid_beta$q$,
	$q$SELECT 1::bigint;$q$,
	'There should be one rapid beta parent for 4.0');

SELECT results_eq(
	$q$SELECT COUNT(*)
	   FROM product_versions WHERE rapid_beta_id IN
	    ( SELECT product_version_id FROM product_versions pv2
		WHERE pv2.version_string = '4.0b' and pv2.is_rapid_beta)$q$,
	$q$SELECT 2::bigint;$q$,
	'There should be two rapid beta releases for 4.0');

SELECT results_eq(
	$q$SELECT COUNT(*) FROM product_versions
		JOIN product_version_builds USING (product_version_id)
		WHERE version_string = '4.0b' and is_rapid_beta$q$,
	$q$SELECT 0::bigint;$q$,
	'The rapid beta parent should have zero builds rows');

SELECT results_eq(
	$q$SELECT COUNT(*) FROM product_versions
		JOIN product_version_builds USING (product_version_id)
		WHERE major_version = '4.0'
			AND beta_number IN (1,2)$q$,
	$q$SELECT 6::bigint;$q$,
	'The rapid beta children should have six builds rows');

-- Finish the tests and clean up.
SELECT * FROM finish();
ROLLBACK;