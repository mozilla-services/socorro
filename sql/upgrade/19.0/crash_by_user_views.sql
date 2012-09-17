\set ON_ERROR_STOP 1

BEGIN;

DROP VIEW IF EXISTS crashes_by_user_build_view;

CREATE OR REPLACE VIEW crashes_by_user_build_view AS
SELECT crashes_by_user_build.product_version_id,
  product_versions.product_name, version_string,
  os_short_name, os_name, crash_type, crash_type_short,
  crashes_by_user_build.build_date,
  sum(report_count) as report_count,
  sum(report_count / throttle) as adjusted_report_count,
  sum(adu) as adu, throttle
FROM crashes_by_user_build
  JOIN product_versions USING (product_version_id)
  JOIN product_release_channels ON
    product_versions.product_name = product_release_channels.product_name
    AND product_versions.build_type = product_release_channels.release_channel
  JOIN os_names USING (os_short_name)
  JOIN crash_types USING (crash_type_id)
WHERE crash_types.include_agg
GROUP BY crashes_by_user_build.product_version_id,
  product_versions.product_name, version_string,
  os_short_name, os_name, crash_type, crash_type_short,
  crashes_by_user_build.build_date, throttle;

ALTER VIEW crashes_by_user_build_view OWNER TO breakpad_rw;

DROP VIEW IF EXISTS crashes_by_user_view;

CREATE OR REPLACE VIEW crashes_by_user_view AS
SELECT crashes_by_user.product_version_id,
  product_versions.product_name, version_string,
  os_short_name, os_name, crash_type, crash_type_short, report_date,
  report_count, (report_count / throttle) as adjusted_report_count,
  adu, throttle
FROM crashes_by_user
  JOIN product_versions USING (product_version_id)
  JOIN product_release_channels ON
    product_versions.product_name = product_release_channels.product_name
    AND product_versions.build_type = product_release_channels.release_channel
  JOIN os_names USING (os_short_name)
  JOIN crash_types USING (crash_type_id)
WHERE crash_types.include_agg;

ALTER VIEW crashes_by_user_view OWNER TO breakpad_rw;