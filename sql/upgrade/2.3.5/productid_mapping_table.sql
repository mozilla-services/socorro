\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists('product_productid_map',$x$
	CREATE TABLE product_productid_map (
		product_name citext not null references products(product_name)
			on update cascade on delete cascade,
		productid text not null primary key
		rewrite boolean not null default false
	);
	
	INSERT INTO product_productid_map 
	VALUES ( 'Fennec', '', false ),
		( 'FennecAndroid', '', true ),
		( 'Firefox', '', false ),
		( 'Thunderbird', '', false ),
		( 'SeaMonkey', '', false ),
		( 'Camino', '', false );
	$x$,
	'breakpad_rw');
	
