-- Functions used to create partitions and their indexes.
-- To use this correctly, you need to have plpgsql as a language.  If you
-- haven't already, you can add this by executing:
--   create procedural language plpgsql;

--
-- Name: exec(text); Type: FUNCTION;
--
CREATE FUNCTION exec(c text) RETURNS void
    AS $$
begin
    execute c;
end;
$$
    LANGUAGE plpgsql;

--
-- Name: make_partition(text, text, text, text, text); Type: FUNCTION;
--
CREATE FUNCTION make_partition(base text, part text, pkey text, loval text, hival text) RETURNS void
    AS $_$
declare
    partname text := base || '_' || part;
    rulename text := 'ins_' || part;
    cmd text;
begin
    cmd := subst('create table $$ ( check($$ >= $$ and $$ < $$) ) inherits ($$)',
                 ARRAY[ quote_ident(partname),
                        quote_ident(pkey),
                        quote_literal(loval),
                        quote_ident(pkey),
                        quote_literal(hival),
                        quote_ident(base) ]);
    execute cmd;
    cmd := subst('create rule $$ as on insert to $$ 
                   where NEW.$$ >= $$ and NEW.$$ < $$
                   do instead insert into $$ values (NEW.*)',
                 ARRAY[ quote_ident(rulename),
                        quote_ident(base),
                        quote_ident(pkey),
                        quote_literal(loval),
                        quote_ident(pkey),
                        quote_literal(hival),
                        quote_ident(partname) ]);
    execute cmd;
end;
$_$
    LANGUAGE plpgsql;

--
-- Name: subst(text, text[]); Type: FUNCTION;
--
CREATE FUNCTION subst(str text, vals text[]) RETURNS text
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
