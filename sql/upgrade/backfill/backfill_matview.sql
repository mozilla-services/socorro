\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists ('matview_control',
$x$
CREATE TABLE matview_control (
	matview citext not null primary key,
	update_function citext not null,
	backfill_function citext not null,
	dependancies citext,
	timing citext not null CHECK (
		timing in 'hourly','daily','cumulative','lastday'),
	enabled boolean not null default true,
	fill_order int not null default 99,
	adu_related boolean not null default false,
	notes text
);
$x$,'postgres');

\set ON_ERROR_STOP 0
-- this may error out if we're doing it for the second time, so ignore errors

\copy matview_control FROM 'matview_update_grid.csv' WITH CSV HEADER