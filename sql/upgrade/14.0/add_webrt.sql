\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM 1 FROM products WHERE product_name = 'WebappRuntime';

IF NOT FOUND THEN

	INSERT INTO products ( product_name,
		sort,
		rapid_release_version,
		release_name
	) VALUES (
		'WebappRuntime',
		7,
		'16.0',
		'webappruntime'
	);

	INSERT INTO product_release_channels (
		product_name, release_channel, throttle )
	SELECT 'WebappRuntime', release_channel, 1.0
	FROM release_channels;

	INSERT INTO product_productid_map (
		product_name, productid, rewrite,
		version_began, version_ended )
	VALUES ( 'WebappRuntime', 'webapprt@mozilla.org', true,
		'0.0',NULL);

	INSERT INTO transform_rules
	(category, rule_order, predicate, predicate_args,
		predicate_kwargs, action, action_args, action_kwargs)
	values
	('processor.json_rewrite', 3,
	'socorro.processor.processor.json_equal_predicate', '',
	'key="ProductName", value="Webapp Runtime"',
	'socorro.processor.processor.json_reformat_action', '',
	'key="ProductName", format_str="WebappRuntime"');

ELSE
	RAISE INFO 'WebRuntime already in database, skipping';

END IF;
END;$f$;