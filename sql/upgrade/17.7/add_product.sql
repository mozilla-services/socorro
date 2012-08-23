-- This Source Code Form is subject to the terms of the Mozilla Public
-- License, v. 2.0. If a copy of the MPL was not distributed with this
-- file, You can obtain one at http://mozilla.org/MPL/2.0/.

\set ON_ERROR_STOP 1

create or replace function add_new_product(
	prodname text,
	initversion major_version,
	prodid text default null,
	ftpname text default null,
	release_throttle numeric default 1.0 )
returns boolean
language plpgsql
as $f$
declare current_sort int;
	rel_name text;
begin

IF prodname IS NULL OR initversion IS NULL THEN
	RAISE EXCEPTION 'a product name and initial version are required';
END IF;

-- check if product already exists
PERFORM 1 FROM products
WHERE product_name = prodname;

IF FOUND THEN
	RAISE INFO 'product % is already in the database';
	RETURN FALSE;
END IF;

-- add the product
SELECT max(sort) INTO current_sort
FROM products;

INSERT INTO products ( product_name, sort, rapid_release_version,
	release_name )
VALUES ( prodname, current_sort + 1, initversion,
	COALESCE(ftpname, prodname));

-- add the release channels

INSERT INTO product_release_channels ( product_name, release_channel )
SELECT prodname, release_channel
FROM release_channels;

-- if throttling, change throttle for release versions

IF release_throttle < 1.0 THEN

	UPDATE product_release_channels
	SET throttle = release_throttle
	WHERE product_name = prodname
		AND release_channel = 'release';

END IF;

-- add the productid map

IF prodid IS NOT NULL THEN
	INSERT INTO product_productid_map ( product_name,
		productid, version_began )
	VALUES ( prodname, prodid, initversion );
END IF;

RETURN TRUE;

END;$f$;




