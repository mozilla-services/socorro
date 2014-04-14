    CREATE VIEW crashes_by_user_build_view AS
    SELECT crashes_by_user_build.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user_build.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user_build.build_date, sum(crashes_by_user_build.report_count) AS report_count, sum(((crashes_by_user_build.report_count)::numeric / product_release_channels.throttle)) AS adjusted_report_count, sum(crashes_by_user_build.adu) AS adu, product_release_channels.throttle
    FROM
        ((((crashes_by_user_build
            JOIN product_versions USING (product_version_id))
            JOIN product_release_channels
                ON (((product_versions.product_name = product_release_channels.product_name)
                AND (product_versions.build_type = product_release_channels.release_channel))))
                        JOIN os_names USING (os_short_name))
                JOIN crash_types USING (crash_type_id))
    GROUP BY crashes_by_user_build.product_version_id, product_versions.product_name, product_versions.version_string, crashes_by_user_build.os_short_name, os_names.os_name, crash_types.crash_type, crash_types.crash_type_short, crashes_by_user_build.build_date, product_release_channels.throttle
;
