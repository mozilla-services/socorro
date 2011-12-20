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
