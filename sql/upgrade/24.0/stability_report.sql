\set ON_ERROR_STOP 1

CREATE OR REPLACE FUNCTION stability_report(
	start_date DATE,
	end_date DATE,
	products TEXT[] default '{}',
	groups TEXT[] default ARRAY['product'] ,
	OUT report_date DATE,
	OUT product CITEXT,
	OUT channel CITEXT,
	OUT version TEXT,
	OUT os_name CITEXT,
	OUT crash_type CITEXT,
	OUT report_count INT,
	OUT adu INT,
	OUT crash_hadu NUMERIC
)
LANGUAGE plpgsql
AS $f$
DECLARE prod_clause TEXT := '';
	group_clause TEXT := '';
	select_clause TEXT := '';
	join_clause TEXT := '';
	std_groups TEXT[];
	std_cols TEXT[];
	bad_val TEXT;
	sgroup INT;
	repquery TEXT;
BEGIN

-- available grouping levels, in correct order
std_groups := ARRAY [ 'product','channel','version','os_name','crash_type' ];
std_cols := ARRAY [ 'product_versions.product_name','product_versions.build_type',
					'product_versions.version', 'os_names.os_name', 'crash_types.crash_type' ];

-- check products list
IF products <> '{}' THEN
	SELECT prods.product
	INTO bad_val
	FROM unnest(products) AS prods(product)
	WHERE prods.product NOT IN ( SELECT product_name FROM products );
	IF bad_val <> '' THEN
		RAISE EXCEPTION 'Product % does not exist.', bad_val;
	ELSE
		prod_clause := ' AND product_versions.product_name IN ( '''
			||  array_to_string(products, ''', ''' ) || ''' ) ';
	END IF;
END IF;

-- check groups list
IF groups <> '{}' THEN
	bad_val := '';
	SELECT groupies.groupy
	INTO bad_val
	FROM unnest(groups) as groupies(groupy)
	WHERE groupy != ALL ( std_groups );
	IF bad_val <> '' THEN
		RAISE EXCEPTION 'Grouping level % is invalid.', bad_val;
	ELSE
		group_clause := ', ' || array_to_string(groups, ', ');
		-- loop through grouping clauses IN ORDER to make sure
		-- that we correctly populate the SELECT and JOIN clauses
		FOR sgroup IN SELECT i FROM generate_series(1,array_upper(std_groups,1)) as gs(i) LOOP

			IF std_groups[sgroup] = ANY ( groups ) THEN
				select_clause := select_clause ||
					', ' || std_cols[sgroup] || ' AS '
					|| std_groups[sgroup];

				-- add join clauses

				IF std_groups[sgroup] = 'os_name' THEN
					join_clause := join_clause || ' JOIN os_names USING ( os_short_name ) ';
				ELSIF std_groups[sgroup] = 'crash_type' THEN
					join_clause := join_clause || ' JOIN crash_types USING ( crash_type_id ) ';
				END IF;
			ELSE
				select_clause := select_clause ||
					', ''''::CITEXT AS ' || std_groups[sgroup];
			END IF;
		END LOOP;
	END IF;
END IF;

repquery := 'SELECT report_date ' || select_clause
	|| ', sum(report_count*throttle)::int AS report_count,
		  sum(adu)::int AS adu,
		  crash_hadu(sum(report_count*throttle)::bigint,sum(adu)) AS crash_hadu
		FROM crashes_by_user
			JOIN product_versions USING ( product_version_id )
			JOIN product_release_channels ON
				product_versions.product_name = product_release_channels.product_name
				AND product_versions.build_type = product_release_channels.release_channel '
	|| join_clause
	|| ' WHERE report_date >= ' || quote_literal(to_char(start_date,'YYYY-MM-DD'))
	|| ' AND report_date <= ' || quote_literal(to_char(start_date,'YYYY-MM-DD'))
	|| prod_clause
	|| ' GROUP BY report_date ' || group_clause
	|| ' ORDER BY report_date ' || group_clause;

RETURN QUERY EXECUTE repquery;
RETURN;

END; $f$;






