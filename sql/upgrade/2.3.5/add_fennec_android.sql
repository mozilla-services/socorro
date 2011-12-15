\set ON_ERROR_STOP 1

DO $f$
BEGIN
PERFORM 1 FROM products WHERE product_name = 'FennecAndroid';
IF NOT FOUND THEN

	UPDATE products SET sort = sort + 1 WHERE sort >= 4;
	
	INSERT INTO products ( product_name, sort, rapid_release_version, release_name )
	VALUES ( 'FennecAndroid', 4, '5.0', 'mobile' );
	
	INSERT INTO product_release_channels ( product_name, release_channel, throttle )
	VALUES ( 'FennecAndroid', 'Nightly', 1.0 ),
	( 'FennecAndroid', 'Aurora', 1.0 ),
	( 'FennecAndroid', 'Beta', 1.0 ),
	( 'FennecAndroid', 'Release', 1.0 );
END IF;
END;
$f$;