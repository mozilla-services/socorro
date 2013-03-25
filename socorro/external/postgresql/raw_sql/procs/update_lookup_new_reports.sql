CREATE FUNCTION update_lookup_new_reports(column_name text) RETURNS boolean
    LANGUAGE plpgsql
    AS $$
declare table_name text;
	insert_query text;
begin
	IF column_name LIKE '%s' THEN
		table_name := column_name || 'es';
	ELSE
		table_name := column_name || 's';
	END IF;
	
	insert_query := '
		insert into ' || table_name || ' ( ' || column_name || ', first_seen )
		select newrecords.* from ( 
			select ' || column_name || '::citext as col,
				min(date_processed) as first_report
			from new_reports
			group by col ) as newrecords
		left join ' || table_name || ' as lookuplist
			on newrecords.col = lookuplist.' || column_name || '
		where lookuplist.' || column_name || ' IS NULL;';
	
	execute insert_query;
	
	RETURN true;
end; $$;


