/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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


