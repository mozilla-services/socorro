\set ON_ERROR_STOP 1


update reports set version = version || 'esr'
where release_channel = 'esr' and version NOT LIKE '%esr'
and date_processed > '2012-01-30';

DO $f$
BEGIN
PERFORM 1 FROM release_channels WHERE release_channel = 'ESR';

IF NOT FOUND THEN

	insert into release_channels ( release_channel, sort )
	values ( 'ESR', 5 );

	insert into release_channel_matches ( release_channel, match_string )
	values ( 'ESR', 'esr' );

	insert into product_release_channels
		(product_name, release_channel, throttle)
	select product_name, 'ESR', 1.0
	from products;
	
END IF;
END; $f$;


update product_versions SET build_type = 'ESR' where version_string like '%esr'
	and build_type <> 'ESR';

