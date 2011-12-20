\set ON_ERROR_STOP 1

DO $f$
DECLARE newprod INT;
BEGIN
PERFORM 1 FROM products WHERE product_name = 'FennecAndroid';
IF NOT FOUND THEN

	UPDATE products SET sort = sort + 1 WHERE sort >= 4;
	
	INSERT INTO products ( product_name, sort, rapid_release_version, release_name )
	VALUES ( 'FennecAndroid', 4, '5.0', '**SPECIAL**' );
	
	INSERT INTO product_release_channels ( product_name, release_channel, throttle )
	VALUES ( 'FennecAndroid', 'Nightly', 1.0 ),
	( 'FennecAndroid', 'Aurora', 1.0 ),
	( 'FennecAndroid', 'Beta', 1.0 ),
	( 'FennecAndroid', 'Release', 1.0 );
	
	newprod := nextval('productdims_id_seq1');
	-- insert fake productdims record as workaround for UI bug
	INSERT INTO productdims ( id, product, version, branch, release )
	VALUES ( newprod, 'FennecAndroid', '0.0', '2.0', 'major' );
	
	INSERT INTO product_visibility ( productdims_id, 
		start_date, end_date, ignore, featured, throttle )
	VALUES ( newprod, '2011-01-01', '2011-02-01', true, false, 100.0 ); 
	
END IF;
END;
$f$;

SELECT update_product_versions();

UPDATE product_versions SET featured = true WHERE product_name = 'FennecAndroid' AND version_string = '11.0a1';
