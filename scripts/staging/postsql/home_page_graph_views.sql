CREATE OR REPLACE VIEW home_page_graph_view
AS
SELECT product_version_id,
  product_name,
  version_string,
  report_date,
  report_count,
  adu,
  crash_hadu
FROM home_page_graph
  JOIN product_versions USING (product_version_id);

ALTER VIEW home_page_graph_view OWNER TO breakpad_rw;


CREATE OR REPLACE VIEW home_page_graph_build_view
AS
SELECT product_version_id,
  product_versions.product_name,
  version_string,
  home_page_graph_build.build_date,
  sum(report_count) as report_count,
  sum(adu) as adu,
  crash_hadu(sum(report_count), sum(adu), throttle) as crash_hadu
FROM home_page_graph_build
  JOIN product_versions USING (product_version_id)
  JOIN product_release_channels ON
       product_versions.product_name = product_release_channels.product_name
          AND product_versions.build_type = product_release_channels.release_channel
GROUP BY product_version_id, product_versions.product_name,
	version_string, home_page_graph_build.build_date, throttle;

ALTER VIEW home_page_graph_build_view OWNER TO breakpad_rw;