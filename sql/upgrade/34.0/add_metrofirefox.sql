\set ON_ERROR_STOP 1

DO $f$
BEGIN

PERFORM 1 FROM products WHERE product_name = 'MetroFirefox';

IF NOT FOUND THEN

        SELECT add_new_product('MetroFirefox','16.0','{{99bceaaa-e3c6-48c1-b981-ef9b46b67d60}}','metrofirefox');

ELSE
	RAISE INFO 'MetroFirefox already in database, skipping';

END IF;
END;$f$;
