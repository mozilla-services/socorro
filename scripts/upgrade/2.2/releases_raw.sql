begin;

-- releases_raw table
-- holds data from FTP scraping
-- updated by daily cron job

create table releases_raw (
	product_name citext not null,
	version text not null,
	platform text not null,
	build_id numeric not null,
	build_type citext not null,
	beta_number int,
	constraint release_raw_key primary key ( product_name, version, build_id, build_type, platform )
);

alter table releases_raw owner to breakpad_rw;

commit;

