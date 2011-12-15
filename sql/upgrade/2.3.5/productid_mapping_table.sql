\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists('product_productid_map',$x$
	CREATE TABLE product_productid_map (
		product_name citext not null references products(product_name)
			on update cascade on delete cascade,
		productid text not null primary key,
		rewrite boolean not null default false,
		version_began major_version not null,
		version_ended major_version,
		constraint productid_map_key2 unique ( product_name, version_began )
	);
	
	INSERT INTO product_productid_map 
	VALUES ( 'Fennec', 'a23983c0-fd0e-11dc-95ff-0800200c9a66', false, '0.1', null ),
		( 'FennecAndroid', 'aa3c5121-dab2-40e2-81ca-7ea25febc110', true, '0.1', null ),
		( 'Firefox', 'ec8030f7-c20a-464f-9b0e-13a3a9e97384', false, '0.7', null ),
		( 'Thunderbird', '3550f703-e582-4d05-9a08-453d09bdfdc6', false, '0.3', null ),
		( 'SeaMonkey', '92650c4d-4b8e-4d2a-b7eb-24ecf4f6b63a', false, '1.0a', null ),
		( 'Camino', 'camino@caminobrowser.org', false, '0.0', null );
	$x$,
	'breakpad_rw');
	
