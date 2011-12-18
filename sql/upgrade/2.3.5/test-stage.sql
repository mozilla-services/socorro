\set ON_ERROR_STOP 1

INSERT INTO releases_raw ( product_name, version, platform, build_id,
	build_type, beta_number, repository )
VALUES ( 'Fennec', '11.0a1', 'android-arm', 20111122030, 'nightly', NULL, 'mozilla-central-android' ),
	( 'Fennec', '11.0a2', 'android-arm', 201111291030, 'aurora', NULL, 'mozilla-central-android' ),
	( 'Fennec', '11.0', 'android', 201112081030, 'beta', 1, 'mozilla-beta' ),
	( 'Fennec', '11.0', 'android', 201112151030, 'release', 1, 'mozilla-release' );
	
SELECT update_product_versions();
