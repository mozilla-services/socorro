-- Functions used to create partitions and their indexes.
-- To use this correctly, you need to have plpgsql as a language.  If you
-- haven't already, you can add this by executing:
--   create procedural language plpgsql;

--
-- Name: make_partition(integer); Type: FUNCTION;
--
CREATE OR REPLACE FUNCTION make_partition(new_partition integer) RETURNS void
    AS $_$
declare
    old_partition integer := new_partition - 1;
    old_start_date text;
    old_end_date text;
    old_end_id integer;
    old_tablename text;
    start_id integer := 0;
    tablename text;
    objname text;
    rulename text;
    cmd text;
begin
    LOCK reports IN ROW EXCLUSIVE MODE;
    LOCK frames IN ROW EXCLUSIVE MODE;
    LOCK dumps IN ROW EXCLUSIVE MODE;
    -- LOCK modules IN ROW EXCLUSIVE MODE;

    if old_partition > 0 then
        old_tablename := 'reports_part' || old_partition::text;
        cmd := subst('SELECT max(id), min(date), max(date) FROM $$',
                     ARRAY[ quote_ident(old_tablename) ]);

        RAISE NOTICE 'cmd: %', cmd;

        execute cmd into old_end_id, old_start_date, old_end_date;

        cmd := subst('ALTER TABLE $$ ADD CHECK( id <= $$ ),
                                     ADD CHECK( date >= $$ AND date <= $$)',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id),
                            quote_literal(old_start_date),
                            quote_literal(old_end_date) ]);
        execute cmd;

        old_tablename := 'frames_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        old_tablename := 'dumps_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        start_id := old_end_id + 1;
    end if;

    tablename := 'reports_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    PRIMARY KEY(id),
                    UNIQUE(uuid),
                    CHECK(id >= $$)
                  ) INHERITS (reports)',
                 ARRAY[ quote_ident(tablename),
                        quote_literal(start_id) ]);
    execute cmd;

    cmd := subst('CREATE OR REPLACE RULE rule_reports_partition AS
                  ON INSERT TO reports
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    objname := 'idx_reports_part' || new_partition::text || '_date';
    cmd := subst('CREATE INDEX $$ ON $$ (date, product, version, build)',
                 ARRAY[ quote_ident(objname),
		        quote_ident(tablename) ]);
    execute cmd;

    objname := 'frames_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id, frame_num),
                    FOREIGN KEY(report_id) REFERENCES $$ (id)
                  ) INHERITS (frames)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    cmd := subst('CREATE OR REPLACE RULE rule_frames_partition AS
                  ON INSERT TO frames
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                  ARRAY [ quote_ident(objname) ]);
    execute cmd;

    objname := 'dumps_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id),
                    FOREIGN KEY(report_id) REFERENCES $$ (id)
                  ) INHERITS (dumps)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    cmd := subst('CREATE OR REPLACE RULE rule_dumps_partition AS
                  ON INSERT TO dumps
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(objname) ]);
    execute cmd;
end;
$_$
    LANGUAGE plpgsql;

--
-- Name: subst(text, text[]); Type: FUNCTION;
--
CREATE OR REPLACE FUNCTION subst(str text, vals text[]) RETURNS text
    AS $_$
declare
    split text[] := string_to_array(str,'$$');
    result text[] := split[1:1];
begin
    for i in 2..array_upper(split,1) loop
        result := result || vals[i-1] || split[i];
    end loop;
    return array_to_string(result,'');
end;
$_$
    LANGUAGE plpgsql IMMUTABLE STRICT;
