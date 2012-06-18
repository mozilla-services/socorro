\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM 1 FROM products WHERE product_name = 'WebRuntime';

IF NOT FOUND THEN

	INSERT INTO products ( product_name,
		sort,
		rapid_release_version,
		release_name
	) VALUES (
		'WebRuntime',
		7,
		'15.0',
		'webruntime'
	);

	INSERT INTO product_release_channels (
		product_name, release_channel, throttle )
	SELECT 'WebRuntime', release_channel, 1.0
	FROM release_channels;

	INSERT INTO product_productid_map (
		product_name, productid, rewrite,
		version_began, version_ended )
	VALUES ( 'WebRuntime', 'webapprt@mozilla.org', true,
		'0.0',NULL);

ELSE
	RAISE INFO 'WebRuntime already in database, skipping';

END IF;
END;$f$;