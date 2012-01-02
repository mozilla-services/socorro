\set ON_ERROR_STOP 1

INSERT INTO releases_raw ( product_name, version, platform, build_id,
	build_type, beta_number, repository )
VALUES ( 'mobile', '11.0a1', 'android-arm', 20111122030291, 'nightly', NULL, 'mozilla-central-android' ),
	( 'mobile', '11.0a2', 'android-arm', 201111291030291, 'aurora', NULL, 'mozilla-central-android' ),
	( 'mobile', '11.0', 'android', 201112081030291, 'beta', 1, 'mozilla-beta' ),
	( 'mobile', '11.0', 'android', 201112151030291, 'release', NULL, 'mozilla-release' );
	
INSERT INTO releases_raw ( product_name, version, platform, build_id,
	build_type, beta_number, repository )
VALUES 
	( 'mobile', '11.0a2', 'android-arm', 201111291030291, 'aurora', NULL, 'mozilla-central-android-xul' ),
	( 'mobile', '11.0', 'android-xul', 201112081030291, 'beta', 1, 'mozilla-beta' ),
	( 'mobile', '11.0', 'android-xul', 201112151030291, 'release', NULL, 'mozilla-release' );
	
SELECT update_product_versions();

INSERT INTO raw_adu ( adu_count, date, product_name, product_os_platform, 
	product_os_version, product_version, build, build_channel, product_guid )
VALUES ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0a1', '201111221030291', 'nightly', 'aa3c5121-dab2-40e2-81ca-7ea25febc110' ),
 ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0a2', '201111291030291', 'aurora', 'aa3c5121-dab2-40e2-81ca-7ea25febc110' ),
 ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0', '201112081030291', 'beta', 'aa3c5121-dab2-40e2-81ca-7ea25febc110' ),
 ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0', '201112151030291', 'release', 'aa3c5121-dab2-40e2-81ca-7ea25febc110' );
	
INSERT INTO raw_adu ( adu_count, date, product_name, product_os_platform, 
	product_os_version, product_version, build, build_channel, product_guid )
VALUES ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0a1', '201111221030291', 'nightly', 'a23983c0-fd0e-11dc-95ff-0800200c9a66' ),
 ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0a2', '201111291030291', 'aurora', 'a23983c0-fd0e-11dc-95ff-0800200c9a66' ),
 ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0', '201112081030291', 'beta', 'a23983c0-fd0e-11dc-95ff-0800200c9a66' ),
 ( ( random() * 2000 )::INT + 5000, '2011-12-20', 'Fennec', 'Linux', NULL,
	'11.0', '201112151030291', 'release', 'a23983c0-fd0e-11dc-95ff-0800200c9a66' );