CREATE OR REPLACE FUNCTION create_weekly_partition(tablename citext, theweek date, partcol text DEFAULT 'date_processed'::text, tableowner text DEFAULT ''::text, uniques text[] DEFAULT '{}'::text[], indexes text[] DEFAULT '{}'::text[], fkeys text[] DEFAULT '{}'::text[], is_utc boolean DEFAULT false, timetype text DEFAULT 'TIMESTAMP'::text) RETURNS boolean
    LANGUAGE plpgsql
    AS $_$
DECLARE dex INT := 1;
    thispart TEXT;
    fkstring TEXT;
BEGIN
-- this function allows you to create a new weekly partition
-- of an existing master table.  it checks if the table is already
-- there and also optionally sets the ownership
-- this version of the function also creates indexes from a list of fields
-- currently only handles single-column indexes and unique declarations
-- supports date, timestamp, timestamptz/utc through the various options

    thispart := tablename || '_' || to_char(theweek, 'YYYYMMDD');

    PERFORM 1 FROM pg_stat_user_tables
    WHERE relname = thispart;
    IF FOUND THEN
        RETURN TRUE;
    END IF;

    IF is_utc THEN
        timetype := ' TIMESTAMPTZ';
    END IF;

    EXECUTE 'CREATE TABLE ' || thispart || ' ( CONSTRAINT ' || thispart
        || '_date_check CHECK ( ' || partcol || ' BETWEEN '
        || timetype || ' ' || quote_literal(to_char(theweek, 'YYYY-MM-DD'))
        || ' AND ' || timetype || ' '
        || quote_literal(to_char(theweek + 7, 'YYYY-MM-DD'))
        || ' ) ) INHERITS ( ' || tablename || ');';

    IF tableowner <> '' THEN
        EXECUTE 'ALTER TABLE ' || thispart || ' OWNER TO ' || tableowner;
    END IF;

    dex := 1;
    WHILE uniques[dex] IS NOT NULL LOOP
        EXECUTE 'CREATE UNIQUE INDEX ' || thispart ||'_'
        || regexp_replace(uniques[dex], $$[,(\s]+$$, '_', 'g')
        || ' ON ' || thispart || '(' || uniques[dex] || ')';
        dex := dex + 1;
    END LOOP;

    dex := 1;
    WHILE indexes[dex] IS NOT NULL LOOP
        EXECUTE 'CREATE INDEX ' || thispart || '_'
        || regexp_replace(indexes[dex], $$[,\s]+$$, '_', 'g')
        || ' ON ' || thispart || '(' || indexes[dex] || ')';
        dex := dex + 1;
    END LOOP;

    dex := 1;
    WHILE fkeys[dex] IS NOT NULL LOOP
        fkstring := regexp_replace(fkeys[dex], 'WEEKNUM', to_char(theweek, 'YYYYMMDD'), 'g');
        EXECUTE 'ALTER TABLE ' || thispart || ' ADD CONSTRAINT '
            || thispart || '_fk_' || dex || ' FOREIGN KEY '
            || fkstring || ' ON DELETE CASCADE ON UPDATE CASCADE';
        dex := dex + 1;
    END LOOP;

    RETURN TRUE;
END;
$_$;


