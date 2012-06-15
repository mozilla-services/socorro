\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION get_product_version_ids (
	product CITEXT,
	VARIADIC versions CITEXT[]
)
returns INT[]
language sql
as $f$
SELECT array_agg(product_version_id) 
FROM product_versions
	WHERE product_name = $1
	AND version_string = ANY ( $2 );
$f$;


