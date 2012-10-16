\set ON_ERROR_STOP 1

-- fix permissions for analyst on new matviews

GRANT SELECT ON crashes_by_user TO analyst;
GRANT SELECT ON crashes_by_user_build TO analyst;
GRANT SELECT ON crashes_by_user_view TO analyst;
GRANT SELECT ON crashes_by_user_build_view TO analyst;
GRANT SELECT ON home_page_graph TO analyst;
GRANT SELECT ON home_page_graph_view TO analyst;
GRANT SELECT ON home_page_graph_build TO analyst;
GRANT SELECT ON home_page_graph_build_view TO analyst;
