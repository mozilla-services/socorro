\set ON_ERROR_STOP 1

SELECT create_table_if_not_exists( 'correlations',
$x$
CREATE TABLE correlations (
	correlation_id SERIAL not null primary key,
	signature_id INT NOT NULL,
	os_name citext NOT NULL,
	reason_id INT NOT NULL,
	crash_count INT NOT NULL default 0,
	CONSTRAINT correlations_key UNIQUE ( signature_id, os_name, reason )
);
$x$,
'breakpad_rw');


SELECT create_table_if_not_exists( 'correlation_addons',
$x$
CREATE TABLE correlation_addons (
	correlation_id not null references correlations(correlation_id),
	addon_key text not null,
	addon_version text not null,
	crash_count INT NOT NULL default 0,
	CONSTRAINT correlation_addons_key UNIQUE ( correlation_id, addon_key, addon_version )
);
$x$,
'breakpad_rw');


SELECT create_table_if_not_exists( 'correlation_modules',
$x$
CREATE TABLE correlation_modules (
	correlation_id not null references correlations(correlation_id),
	module_signature text not null,
	module_version text not null,
	crash_count INT NOT NULL default 0,
	CONSTRAINT correlation_modules_key UNIQUE ( correlation_id, module_key, module_version )
);
$x$,
'breakpad_rw');
