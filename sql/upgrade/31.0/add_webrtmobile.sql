\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM 1 FROM products WHERE product_name = 'WebappRuntimeMobile';

IF NOT FOUND THEN

    PERFORM add_new_product('WebAppRuntimeMobile','16.0','{webapprtmobile@mozilla.com}','webapprtmobile');

	INSERT INTO transform_rules
	(category, rule_order, predicate, predicate_args,
		predicate_kwargs, action, action_args, action_kwargs)
	values
	('processor.json_rewrite', 3,
	'socorro.processor.processor.json_equal_predicate', '',
	'key="ProductName", value="Webapp Runtime Mobile"',
	'socorro.processor.processor.json_reformat_action', '',
	'key="ProductName", format_str="WebappRuntimeMobile"');

ELSE
	RAISE INFO 'WebRuntimeMobile already in database, skipping';

END IF;
END;$f$;
