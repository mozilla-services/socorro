CREATE VIEW crashes_by_user_rollup AS
    SELECT crashes_by_user.product_version_id, crashes_by_user.report_date, crashes_by_user.os_short_name, sum(crashes_by_user.report_count) AS report_count, min(crashes_by_user.adu) AS adu FROM (crashes_by_user JOIN crash_types USING (crash_type_id)) WHERE crash_types.include_agg GROUP BY crashes_by_user.product_version_id, crashes_by_user.report_date, crashes_by_user.os_short_name
;
