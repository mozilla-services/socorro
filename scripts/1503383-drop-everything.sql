--
-- Bug 1503383: drop everything
--
-- Drops all the stored procedures and things that we don't need anymore.

BEGIN WORK;

-- Drop functions
DROP FUNCTION IF EXISTS version_sort_digit(text);
DROP FUNCTION IF EXISTS major_version_sort(text);
DROP FUNCTION IF EXISTS add_new_product(text, major_version, text, text, numeric, numeric);
DROP FUNCTION IF EXISTS add_new_release(citext, citext, citext, numeric, citext, integer, text, text, boolean, boolean);
DROP FUNCTION IF EXISTS build_date(numeric);
DROP FUNCTION IF EXISTS build_numeric(character varying);
DROP FUNCTION IF EXISTS is_rapid_beta(text, text, text);
DROP FUNCTION IF EXISTS major_version(text);
DROP FUNCTION IF EXISTS nonzero_string(citext);
DROP FUNCTION IF EXISTS nonzero_string(text);
DROP FUNCTION IF EXISTS old_version_sort(text);
DROP FUNCTION IF EXISTS product_version_sort_number(text);
DROP FUNCTION IF EXISTS sunset_date(numeric, text);
DROP FUNCTION IF EXISTS to_major_version(text);
DROP FUNCTION IF EXISTS update_product_versions(integer);
DROP FUNCTION IF EXISTS version_matches_channel(text, citext);
DROP FUNCTION IF EXISTS version_sort(text, integer, citext);
DROP FUNCTION IF EXISTS version_sort_trigger();
DROP FUNCTION IF EXISTS version_sort_update_trigger_after();
DROP FUNCTION IF EXISTS version_sort_update_trigger_before();
DROP FUNCTION IF EXISTS version_string(text, integer);
DROP FUNCTION IF EXISTS version_string(text, integer, text);

-- Drop tables we definitely don't need
DROP TABLE IF EXISTS crontabber_log;
DROP TABLE IF EXISTS crontabber;
DROP TABLE IF EXISTS product_build_types;
DROP TABLE IF EXISTS product_productid_map;
DROP TABLE IF EXISTS product_release_channels;
DROP TABLE IF EXISTS product_version_builds;
DROP TABLE IF EXISTS product_versions;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS release_channels;
DROP TABLE IF EXISTS release_repositories;
DROP TABLE IF EXISTS releases_raw;
DROP TABLE IF EXISTS special_product_platforms;

COMMIT WORK;
