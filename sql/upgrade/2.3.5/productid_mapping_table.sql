\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists('product_productid_map',$x$
	CREATE TABLE product_productid_map (
		product_name citext not null references products(product_name)
			on update cascade on delete cascade,
		productid text not null primary key,
		rewrite boolean not null default false,
		began date not null default current_date,
		ended date
	);
	
	INSERT INTO product_productid_map 
	VALUES ( 'Fennec', 'a23983c0-fd0e-11dc-95ff-0800200c9a66', false, '2011-01-01', null ),
		( 'FennecAndroid', 'FA-GUID-not-assigned-yet', true, '2011-01-01', null ),
		( 'Firefox', 'ec8030f7-c20a-464f-9b0e-13a3a9e97384', false, '2011-01-01', null ),
		( 'Thunderbird', '3550f703-e582-4d05-9a08-453d09bdfdc6', false, '2011-01-01', null ),
		( 'SeaMonkey', '92650c4d-4b8e-4d2a-b7eb-24ecf4f6b63a', false, '2011-01-01', null ),
		( 'Camino', 'No-GUID-for-Camino', false, '2011-01-01', null );
	$x$,
	'breakpad_rw');
	
