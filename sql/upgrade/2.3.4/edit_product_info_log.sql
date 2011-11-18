-- add logging to edit_product_info
-- so that we can see who's been changing dates

-- we're using a composite record type to represent the 
-- before and after records
create type product_info_change (
	begin_date date
	end_date date,
	featured boolean,
	crash_throttle numeric
);

create or replace table product_info_changelog (
	product_version_id int not null,
	user_name text not null,
	changed_on timestamptz not null,
	oldrec product_info_change,
	newrec product_info_change,
	constraint product_info_changelog_key primary key (product_version_id, changed_on, user_name )
);


create or replace function edit_product_info (
	prod_id INT,
	prod_name citext,
	prod_version text,
	prod_channel text,
	begin_visibility date,
	end_visibility date,
	is_featured boolean,
	crash_throttle numeric,
	user_name text default ''
)
RETURNS INT
LANGUAGE plpgsql
AS $f$
DECLARE which_t text;
	new_id INT;

-- this function allows the admin UI to edit product and version
-- information regardless of which table it appears in
-- currently editing the new products is limited to
-- visibility dates and featured because of the need to supply
-- build numbers, and that we're not sure it will ever
-- be required.
-- does not validate required fields or duplicates
-- trusting to the python code and table constraints to do that

-- will be phased out when we can ignore the old productdims

BEGIN

IF prod_id IS NULL AND prod_version THEN
-- new entry
-- adding rows is only allowed to the old table since the new
-- table is populated automatically
-- see if this is supposed to be in the new table and error out
	PERFORM 1
	FROM products
	WHERE product_name = prod_name
		AND major_version_sort(prod_version) >= major_version_sort(rapid_release_version);
	IF FOUND AND prod_version NOT LIKE '%a%' THEN
		RAISE EXCEPTION 'Product % version % will be automatically updated by the new system.  As such, you may not add this product & version manually.',prod_name,prod_version;
	ELSE

		INSERT INTO productdims ( product, version, branch, release )
		VALUES ( prod_name, prod_version, '2.2',
			CASE WHEN prod_channel ILIKE 'beta' THEN 'milestone'::release_enum
				WHEN prod_channel ILIKE 'aurora' THEN 'development'::release_enum
				WHEN prod_channel ILIKE 'nightly' THEN 'development'::release_enum
				ELSE 'major' END )
		RETURNING id
		INTO new_id;

		INSERT INTO product_visibility ( productdims_id, start_date, end_date, featured, throttle )
		VALUES ( new_id, begin_visibility, end_visibility, is_featured, crash_throttle );

	END IF;

ELSE

-- first, find out whether we're dealing with the old or new table
	SELECT which_table INTO which_t
	FROM product_info WHERE product_version_id = prod_id;

	IF NOT FOUND THEN
		RAISE EXCEPTION 'No product with that ID was found.  Database Error.';
	END IF;

	IF which_t = 'new' THEN
		-- note that changes to the product name or version will be ignored
		-- only changes to featured and visibility dates will be taken
		
		-- first we're going to log this since we've had some issues
		-- and we want to track updates
		INSERT INTO product_info_changelog (
			product_version_id, user_name, changed_on,
			oldrec, newrec )
		SELECT prod_id, user_name, now(),
			row( build_date, sunset_date,
				featured_version, throttle )
			row( begin_visibility, end_visiblity, 
				is_featured, crash_throttle )
		FROM product_versions JOIN product_release_channels
			ON product_versions.product_name = product_release_channels.product_name
			AND product_versions.build_type = product_release_channels.release_channel
		WHERE product_version_id = prod_id;
		
		-- then update
		UPDATE product_versions SET
			featured_version = is_featured,
			build_date = begin_visibility,
			sunset_date = end_visibility
		WHERE product_version_id = prod_id;

		UPDATE product_release_channels
		SET throttle = crash_throttle / 100
		WHERE product_name = prod_name
			AND release_channel = prod_channel;

		new_id := prod_id;
	ELSE
		UPDATE productdims SET
			product = prod_name,
			version = prod_version,
			release = ( CASE WHEN prod_channel ILIKE 'beta' THEN 'milestone'::release_enum
				WHEN prod_channel ILIKE 'aurora' THEN 'development'::release_enum
				WHEN prod_channel ILIKE 'nightly' THEN 'development'::release_enum
				ELSE 'major' END )
		WHERE id = prod_id;

		UPDATE product_visibility SET
			featured = is_featured,
			start_date = begin_visibility,
			end_date = end_visibility,
			throttle = crash_throttle
		WHERE productdims_id = prod_id;

		new_id := prod_id;
	END IF;
END IF;

RETURN new_id;
END; $f$;
