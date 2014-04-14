CREATE VIEW home_page_graph_view AS
    SELECT home_page_graph.product_version_id, product_versions.product_name, product_versions.version_string, home_page_graph.report_date, home_page_graph.report_count, home_page_graph.adu, home_page_graph.crash_hadu FROM (home_page_graph JOIN product_versions USING (product_version_id))
;
