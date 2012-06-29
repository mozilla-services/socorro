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

-- Load the TAP functions.
BEGIN;

-- Plan the tests.
SELECT plan(72);

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

-- check that tables were dropped
DO $f$
DECLARE tabdropped TEXT[];
	arrpos INT := 1;
	testmsg TEXT := '';
BEGIN
	tabdropped := ARRAY['alexa_topsites','top_crashes_by_signature','top_crashes_by_url','top_crashes_by_url_signature',
		'signature_build','signature_first','signature_bugs_rollup','signature_productdims','release_build_type_map',
		'builds','osdims','product_version_sort','product_visibility','productdims','urldims','daily_crashes',
		'daily_crash_codes'];

	WHILE tabdropped[arrpos] IS NOT NULL LOOP
		testmsg := testmsg || E'\n' || hasnt_table(tabdropped[arrpos], 'table ' || tabdropped[arrpos] || ' should no longer exist.');
		arrpos := arrpos + 1;
	END LOOP;

RAISE INFO '%',testmsg;
END;$f$;

-- check that all the functions exist
DO $f$
DECLARE funcs TEXT[];
	arrpos INT := 1;
	testmsg TEXT := '';
BEGIN
	funcs := ARRAY['backfill_tcbs_build','backfill_tcbs','update_build_adu','backfill_build_adu','update_crashes_by_user_build',
		'backfill_crashes_by_user_build','update_crashes_by_user','backfill_crashes_by_user','update_home_page_graph',
		'backfill_home_page_graph','update_home_page_graph_build','backfill_home_page_graph_build','reports_clean_done',
		'crash_hadu','is_rapid_beta','update_adu','backfill_adu','update_product_versions','update_tcbs_build',
		'update_tcbs'];

	WHILE funcs[arrpos] IS NOT NULL LOOP
		testmsg := testmsg || E'\n' || has_function(funcs[arrpos], 'function ' || funcs[arrpos] || ' should exist.');
		arrpos := arrpos + 1;
	END LOOP;

RAISE INFO '%',testmsg;
END;$f$;

-- check reports_clean_done
SELECT has_function('reports_clean_done', ARRAY['date','interval'], 'reports_clean_done should have check_period parameter');

-- check that all the views exist
DO $f$
DECLARE views TEXT[];
	arrpos INT := 1;
	testmsg TEXT := '';
BEGIN
	views := ARRAY['product_info','product_selector','default_versions_builds','product_crash_ratio',
			'product_os_crash_ratio'];

	WHILE views[arrpos] IS NOT NULL LOOP
		testmsg := testmsg || E'\n' || has_view(views[arrpos], 'view ' || views[arrpos] || ' should exist.');
		arrpos := arrpos + 1;
	END LOOP;

RAISE INFO '%',testmsg;
END;$f$;

--check that update_product_versions executes without error
SELECT lives_ok('SELECT update_product_versions();', 'update_product_versions should execute without error');

-- check that all the update functions execute without errors
DO $f$
DECLARE funcs TEXT[];
	arrpos INT := 1;
	testmsg TEXT := '';
BEGIN
	funcs := ARRAY['backfill_tcbs_build','backfill_tcbs','update_build_adu','backfill_build_adu','update_crashes_by_user_build',
		'backfill_crashes_by_user_build','update_crashes_by_user','backfill_crashes_by_user','update_home_page_graph',
		'backfill_home_page_graph','update_home_page_graph_build','backfill_home_page_graph_build',
		'update_adu','backfill_adu','update_tcbs_build','update_tcbs'];

	SET LOCAL CLIENT_MIN_MESSAGES = ERROR;

	WHILE funcs[arrpos] IS NOT NULL LOOP
		IF funcs[arrpos] LIKE 'update%' THEN
			testmsg := testmsg || E'\n' || lives_ok(
				'SELECT ' || funcs[arrpos] || '(''2012-10-01'',FALSE);',
				'function ' || funcs[arrpos] || ' should execute without errors');
		ELSE
			testmsg := testmsg || E'\n' || lives_ok(
				'SELECT ' || funcs[arrpos] || '(''2012-10-01'');',
				'function ' || funcs[arrpos] || ' should execute without errors');
		END IF;
		arrpos := arrpos + 1;
	END LOOP;

	SET LOCAL CLIENT_MIN_MESSAGES = WARNING;

RAISE INFO '%',testmsg;
END;$f$;


-- Finish the tests and clean up.
SELECT * FROM finish();
ROLLBACK;