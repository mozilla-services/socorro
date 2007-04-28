--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS 'Standard public schema';


--
-- Name: plpgsql; Type: PROCEDURAL LANGUAGE; Schema: -; Owner: postgres
--

CREATE PROCEDURAL LANGUAGE plpgsql;


SET search_path = public, pg_catalog;

--
-- Name: exec(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION exec(c text) RETURNS void
    AS $$

begin

    execute c;

end;

$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.exec(c text) OWNER TO postgres;

--
-- Name: make_partition(text, text, text, text, text); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.make_partition(base text, part text, pkey text, loval text, hival text) OWNER TO postgres;

--
-- Name: subst(text, text[]); Type: FUNCTION; Schema: public; Owner: postgres
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


ALTER FUNCTION public.subst(str text, vals text[]) OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: dumps; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE dumps (
    id integer NOT NULL,
    report_id integer,
    data text
);


ALTER TABLE public.dumps OWNER TO postgres;

--
-- Name: dumps_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE dumps_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.dumps_id_seq OWNER TO postgres;

--
-- Name: dumps_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE dumps_id_seq OWNED BY dumps.id;


--
-- Name: frames; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE frames (
    id integer NOT NULL,
    report_id integer,
    thread_num integer,
    frame_num integer,
    module_name character varying,
    function_name character varying,
    source character varying,
    source_line integer,
    instruction character varying
);


ALTER TABLE public.frames OWNER TO postgres;

--
-- Name: frames_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE frames_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.frames_id_seq OWNER TO postgres;

--
-- Name: frames_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE frames_id_seq OWNED BY frames.id;


--
-- Name: reports; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports (
    id integer NOT NULL,
    date timestamp without time zone NOT NULL,
    signature character varying NOT NULL,
    last_crash timestamp without time zone,
    install_age timestamp without time zone,
    url character varying,
    "comment" text,
    os_name character varying,
    os_version character varying,
    cpu_name character varying,
    cpu_info character varying,
    reason text,
    address character varying,
    product character varying,
    version character varying,
    build character varying,
    platform character varying,
    uuid character varying
);


ALTER TABLE public.reports OWNER TO postgres;

--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE reports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.reports_id_seq OWNER TO postgres;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE reports_id_seq OWNED BY reports.id;


--
-- Name: reports_2007_01; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_01 (CONSTRAINT reports_2007_01_date_check CHECK (((date >= '2007-01-01 00:00:00'::timestamp without time zone) AND (date < '2007-02-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_01 OWNER TO postgres;

--
-- Name: reports_2007_02; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_02 (CONSTRAINT reports_2007_02_date_check CHECK (((date >= '2007-02-01 00:00:00'::timestamp without time zone) AND (date < '2007-03-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_02 OWNER TO postgres;

--
-- Name: reports_2007_03; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_03 (CONSTRAINT reports_2007_03_date_check CHECK (((date >= '2007-03-01 00:00:00'::timestamp without time zone) AND (date < '2007-04-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_03 OWNER TO postgres;

--
-- Name: reports_2007_04; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_04 (CONSTRAINT reports_2007_04_date_check CHECK (((date >= '2007-04-01 00:00:00'::timestamp without time zone) AND (date < '2007-05-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_04 OWNER TO postgres;

--
-- Name: reports_2007_05; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_05 (CONSTRAINT reports_2007_05_date_check CHECK (((date >= '2007-05-01 00:00:00'::timestamp without time zone) AND (date < '2007-06-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_05 OWNER TO postgres;

--
-- Name: reports_2007_06; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_06 (CONSTRAINT reports_2007_06_date_check CHECK (((date >= '2007-06-01 00:00:00'::timestamp without time zone) AND (date < '2007-07-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_06 OWNER TO postgres;

--
-- Name: reports_2007_07; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_07 (CONSTRAINT reports_2007_07_date_check CHECK (((date >= '2007-07-01 00:00:00'::timestamp without time zone) AND (date < '2007-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_07 OWNER TO postgres;

--
-- Name: reports_2007_08; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_08 (CONSTRAINT reports_2007_08_date_check CHECK (((date >= '2007-08-01 00:00:00'::timestamp without time zone) AND (date < '2007-09-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_08 OWNER TO postgres;

--
-- Name: reports_2007_09; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_09 (CONSTRAINT reports_2007_09_date_check CHECK (((date >= '2007-09-01 00:00:00'::timestamp without time zone) AND (date < '2007-10-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_09 OWNER TO postgres;

--
-- Name: reports_2007_10; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_10 (CONSTRAINT reports_2007_10_date_check CHECK (((date >= '2007-10-01 00:00:00'::timestamp without time zone) AND (date < '2007-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_10 OWNER TO postgres;

--
-- Name: reports_2007_11; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_11 (CONSTRAINT reports_2007_11_date_check CHECK (((date >= '2007-11-01 00:00:00'::timestamp without time zone) AND (date < '2007-12-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_11 OWNER TO postgres;

--
-- Name: reports_2007_12; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2007_12 (CONSTRAINT reports_2007_12_date_check CHECK (((date >= '2007-12-01 00:00:00'::timestamp without time zone) AND (date < '2008-01-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2007_12 OWNER TO postgres;

--
-- Name: reports_2008_01; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_01 (CONSTRAINT reports_2008_01_date_check CHECK (((date >= '2008-01-01 00:00:00'::timestamp without time zone) AND (date < '2008-02-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_01 OWNER TO postgres;

--
-- Name: reports_2008_02; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_02 (CONSTRAINT reports_2008_02_date_check CHECK (((date >= '2008-02-01 00:00:00'::timestamp without time zone) AND (date < '2008-03-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_02 OWNER TO postgres;

--
-- Name: reports_2008_03; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_03 (CONSTRAINT reports_2008_03_date_check CHECK (((date >= '2008-03-01 00:00:00'::timestamp without time zone) AND (date < '2008-04-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_03 OWNER TO postgres;

--
-- Name: reports_2008_04; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_04 (CONSTRAINT reports_2008_04_date_check CHECK (((date >= '2008-04-01 00:00:00'::timestamp without time zone) AND (date < '2008-05-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_04 OWNER TO postgres;

--
-- Name: reports_2008_05; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_05 (CONSTRAINT reports_2008_05_date_check CHECK (((date >= '2008-05-01 00:00:00'::timestamp without time zone) AND (date < '2008-06-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_05 OWNER TO postgres;

--
-- Name: reports_2008_06; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_06 (CONSTRAINT reports_2008_06_date_check CHECK (((date >= '2008-06-01 00:00:00'::timestamp without time zone) AND (date < '2008-07-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_06 OWNER TO postgres;

--
-- Name: reports_2008_07; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_07 (CONSTRAINT reports_2008_07_date_check CHECK (((date >= '2008-07-01 00:00:00'::timestamp without time zone) AND (date < '2008-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_07 OWNER TO postgres;

--
-- Name: reports_2008_08; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_08 (CONSTRAINT reports_2008_08_date_check CHECK (((date >= '2008-08-01 00:00:00'::timestamp without time zone) AND (date < '2008-09-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_08 OWNER TO postgres;

--
-- Name: reports_2008_09; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_09 (CONSTRAINT reports_2008_09_date_check CHECK (((date >= '2008-09-01 00:00:00'::timestamp without time zone) AND (date < '2008-10-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_09 OWNER TO postgres;

--
-- Name: reports_2008_10; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_10 (CONSTRAINT reports_2008_10_date_check CHECK (((date >= '2008-10-01 00:00:00'::timestamp without time zone) AND (date < '2008-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_10 OWNER TO postgres;

--
-- Name: reports_2008_11; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_11 (CONSTRAINT reports_2008_11_date_check CHECK (((date >= '2008-11-01 00:00:00'::timestamp without time zone) AND (date < '2008-12-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_11 OWNER TO postgres;

--
-- Name: reports_2008_12; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2008_12 (CONSTRAINT reports_2008_12_date_check CHECK (((date >= '2008-12-01 00:00:00'::timestamp without time zone) AND (date < '2009-01-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2008_12 OWNER TO postgres;

--
-- Name: reports_2009_01; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_01 (CONSTRAINT reports_2009_01_date_check CHECK (((date >= '2009-01-01 00:00:00'::timestamp without time zone) AND (date < '2009-02-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_01 OWNER TO postgres;

--
-- Name: reports_2009_02; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_02 (CONSTRAINT reports_2009_02_date_check CHECK (((date >= '2009-02-01 00:00:00'::timestamp without time zone) AND (date < '2009-03-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_02 OWNER TO postgres;

--
-- Name: reports_2009_03; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_03 (CONSTRAINT reports_2009_03_date_check CHECK (((date >= '2009-03-01 00:00:00'::timestamp without time zone) AND (date < '2009-04-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_03 OWNER TO postgres;

--
-- Name: reports_2009_04; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_04 (CONSTRAINT reports_2009_04_date_check CHECK (((date >= '2009-04-01 00:00:00'::timestamp without time zone) AND (date < '2009-05-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_04 OWNER TO postgres;

--
-- Name: reports_2009_05; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_05 (CONSTRAINT reports_2009_05_date_check CHECK (((date >= '2009-05-01 00:00:00'::timestamp without time zone) AND (date < '2009-06-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_05 OWNER TO postgres;

--
-- Name: reports_2009_06; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_06 (CONSTRAINT reports_2009_06_date_check CHECK (((date >= '2009-06-01 00:00:00'::timestamp without time zone) AND (date < '2009-07-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_06 OWNER TO postgres;

--
-- Name: reports_2009_07; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_07 (CONSTRAINT reports_2009_07_date_check CHECK (((date >= '2009-07-01 00:00:00'::timestamp without time zone) AND (date < '2009-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_07 OWNER TO postgres;

--
-- Name: reports_2009_08; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_08 (CONSTRAINT reports_2009_08_date_check CHECK (((date >= '2009-08-01 00:00:00'::timestamp without time zone) AND (date < '2009-09-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_08 OWNER TO postgres;

--
-- Name: reports_2009_09; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_09 (CONSTRAINT reports_2009_09_date_check CHECK (((date >= '2009-09-01 00:00:00'::timestamp without time zone) AND (date < '2009-10-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_09 OWNER TO postgres;

--
-- Name: reports_2009_10; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_10 (CONSTRAINT reports_2009_10_date_check CHECK (((date >= '2009-10-01 00:00:00'::timestamp without time zone) AND (date < '2009-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_10 OWNER TO postgres;

--
-- Name: reports_2009_11; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_11 (CONSTRAINT reports_2009_11_date_check CHECK (((date >= '2009-11-01 00:00:00'::timestamp without time zone) AND (date < '2009-12-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_11 OWNER TO postgres;

--
-- Name: reports_2009_12; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2009_12 (CONSTRAINT reports_2009_12_date_check CHECK (((date >= '2009-12-01 00:00:00'::timestamp without time zone) AND (date < '2010-01-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2009_12 OWNER TO postgres;

--
-- Name: reports_2010_01; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_01 (CONSTRAINT reports_2010_01_date_check CHECK (((date >= '2010-01-01 00:00:00'::timestamp without time zone) AND (date < '2010-02-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_01 OWNER TO postgres;

--
-- Name: reports_2010_02; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_02 (CONSTRAINT reports_2010_02_date_check CHECK (((date >= '2010-02-01 00:00:00'::timestamp without time zone) AND (date < '2010-03-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_02 OWNER TO postgres;

--
-- Name: reports_2010_03; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_03 (CONSTRAINT reports_2010_03_date_check CHECK (((date >= '2010-03-01 00:00:00'::timestamp without time zone) AND (date < '2010-04-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_03 OWNER TO postgres;

--
-- Name: reports_2010_04; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_04 (CONSTRAINT reports_2010_04_date_check CHECK (((date >= '2010-04-01 00:00:00'::timestamp without time zone) AND (date < '2010-05-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_04 OWNER TO postgres;

--
-- Name: reports_2010_05; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_05 (CONSTRAINT reports_2010_05_date_check CHECK (((date >= '2010-05-01 00:00:00'::timestamp without time zone) AND (date < '2010-06-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_05 OWNER TO postgres;

--
-- Name: reports_2010_06; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_06 (CONSTRAINT reports_2010_06_date_check CHECK (((date >= '2010-06-01 00:00:00'::timestamp without time zone) AND (date < '2010-07-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_06 OWNER TO postgres;

--
-- Name: reports_2010_07; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_07 (CONSTRAINT reports_2010_07_date_check CHECK (((date >= '2010-07-01 00:00:00'::timestamp without time zone) AND (date < '2010-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_07 OWNER TO postgres;

--
-- Name: reports_2010_08; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_08 (CONSTRAINT reports_2010_08_date_check CHECK (((date >= '2010-08-01 00:00:00'::timestamp without time zone) AND (date < '2010-09-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_08 OWNER TO postgres;

--
-- Name: reports_2010_09; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_09 (CONSTRAINT reports_2010_09_date_check CHECK (((date >= '2010-09-01 00:00:00'::timestamp without time zone) AND (date < '2010-10-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_09 OWNER TO postgres;

--
-- Name: reports_2010_10; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_10 (CONSTRAINT reports_2010_10_date_check CHECK (((date >= '2010-10-01 00:00:00'::timestamp without time zone) AND (date < '2010-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_10 OWNER TO postgres;

--
-- Name: reports_2010_11; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_11 (CONSTRAINT reports_2010_11_date_check CHECK (((date >= '2010-11-01 00:00:00'::timestamp without time zone) AND (date < '2010-12-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_11 OWNER TO postgres;

--
-- Name: reports_2010_12; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2010_12 (CONSTRAINT reports_2010_12_date_check CHECK (((date >= '2010-12-01 00:00:00'::timestamp without time zone) AND (date < '2011-01-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2010_12 OWNER TO postgres;

--
-- Name: reports_2011_01; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_01 (CONSTRAINT reports_2011_01_date_check CHECK (((date >= '2011-01-01 00:00:00'::timestamp without time zone) AND (date < '2011-02-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_01 OWNER TO postgres;

--
-- Name: reports_2011_02; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_02 (CONSTRAINT reports_2011_02_date_check CHECK (((date >= '2011-02-01 00:00:00'::timestamp without time zone) AND (date < '2011-03-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_02 OWNER TO postgres;

--
-- Name: reports_2011_03; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_03 (CONSTRAINT reports_2011_03_date_check CHECK (((date >= '2011-03-01 00:00:00'::timestamp without time zone) AND (date < '2011-04-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_03 OWNER TO postgres;

--
-- Name: reports_2011_04; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_04 (CONSTRAINT reports_2011_04_date_check CHECK (((date >= '2011-04-01 00:00:00'::timestamp without time zone) AND (date < '2011-05-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_04 OWNER TO postgres;

--
-- Name: reports_2011_05; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_05 (CONSTRAINT reports_2011_05_date_check CHECK (((date >= '2011-05-01 00:00:00'::timestamp without time zone) AND (date < '2011-06-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_05 OWNER TO postgres;

--
-- Name: reports_2011_06; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_06 (CONSTRAINT reports_2011_06_date_check CHECK (((date >= '2011-06-01 00:00:00'::timestamp without time zone) AND (date < '2011-07-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_06 OWNER TO postgres;

--
-- Name: reports_2011_07; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_07 (CONSTRAINT reports_2011_07_date_check CHECK (((date >= '2011-07-01 00:00:00'::timestamp without time zone) AND (date < '2011-08-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_07 OWNER TO postgres;

--
-- Name: reports_2011_08; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_08 (CONSTRAINT reports_2011_08_date_check CHECK (((date >= '2011-08-01 00:00:00'::timestamp without time zone) AND (date < '2011-09-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_08 OWNER TO postgres;

--
-- Name: reports_2011_09; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_09 (CONSTRAINT reports_2011_09_date_check CHECK (((date >= '2011-09-01 00:00:00'::timestamp without time zone) AND (date < '2011-10-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_09 OWNER TO postgres;

--
-- Name: reports_2011_10; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_10 (CONSTRAINT reports_2011_10_date_check CHECK (((date >= '2011-10-01 00:00:00'::timestamp without time zone) AND (date < '2011-11-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_10 OWNER TO postgres;

--
-- Name: reports_2011_11; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_11 (CONSTRAINT reports_2011_11_date_check CHECK (((date >= '2011-11-01 00:00:00'::timestamp without time zone) AND (date < '2011-12-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_11 OWNER TO postgres;

--
-- Name: reports_2011_12; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_2011_12 (CONSTRAINT reports_2011_12_date_check CHECK (((date >= '2011-12-01 00:00:00'::timestamp without time zone) AND (date < '2012-01-01 00:00:00'::timestamp without time zone)))
)
INHERITS (reports);


ALTER TABLE public.reports_2011_12 OWNER TO postgres;

--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE dumps ALTER COLUMN id SET DEFAULT nextval('dumps_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE frames ALTER COLUMN id SET DEFAULT nextval('frames_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE reports ALTER COLUMN id SET DEFAULT nextval('reports_id_seq'::regclass);


--
-- Name: dumps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY dumps
    ADD CONSTRAINT dumps_pkey PRIMARY KEY (id);


--
-- Name: frames_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY frames
    ADD CONSTRAINT frames_pkey PRIMARY KEY (id);


--
-- Name: reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: report_id; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX report_id ON frames USING btree (report_id, module_name, function_name);


--
-- Name: reports_2007_01_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_01_idx ON reports_2007_01 USING btree (date);


--
-- Name: reports_2007_02_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_02_idx ON reports_2007_02 USING btree (date);


--
-- Name: reports_2007_03_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_03_idx ON reports_2007_03 USING btree (date);


--
-- Name: reports_2007_04_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_04_idx ON reports_2007_04 USING btree (date);


--
-- Name: reports_2007_05_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_05_idx ON reports_2007_05 USING btree (date);


--
-- Name: reports_2007_06_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_06_idx ON reports_2007_06 USING btree (date);


--
-- Name: reports_2007_07_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_07_idx ON reports_2007_07 USING btree (date);


--
-- Name: reports_2007_08_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_08_idx ON reports_2007_08 USING btree (date);


--
-- Name: reports_2007_09_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_09_idx ON reports_2007_09 USING btree (date);


--
-- Name: reports_2007_10_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_10_idx ON reports_2007_10 USING btree (date);


--
-- Name: reports_2007_11_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_11_idx ON reports_2007_11 USING btree (date);


--
-- Name: reports_2007_12_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2007_12_idx ON reports_2007_12 USING btree (date);


--
-- Name: reports_2008_01_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_01_idx ON reports_2008_01 USING btree (date);


--
-- Name: reports_2008_02_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_02_idx ON reports_2008_02 USING btree (date);


--
-- Name: reports_2008_03_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_03_idx ON reports_2008_03 USING btree (date);


--
-- Name: reports_2008_04_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_04_idx ON reports_2008_04 USING btree (date);


--
-- Name: reports_2008_05_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_05_idx ON reports_2008_05 USING btree (date);


--
-- Name: reports_2008_06_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_06_idx ON reports_2008_06 USING btree (date);


--
-- Name: reports_2008_07_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_07_idx ON reports_2008_07 USING btree (date);


--
-- Name: reports_2008_08_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_08_idx ON reports_2008_08 USING btree (date);


--
-- Name: reports_2008_09_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_09_idx ON reports_2008_09 USING btree (date);


--
-- Name: reports_2008_10_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_10_idx ON reports_2008_10 USING btree (date);


--
-- Name: reports_2008_11_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_11_idx ON reports_2008_11 USING btree (date);


--
-- Name: reports_2008_12_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2008_12_idx ON reports_2008_12 USING btree (date);


--
-- Name: reports_2009_01_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_01_idx ON reports_2009_01 USING btree (date);


--
-- Name: reports_2009_02_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_02_idx ON reports_2009_02 USING btree (date);


--
-- Name: reports_2009_03_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_03_idx ON reports_2009_03 USING btree (date);


--
-- Name: reports_2009_04_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_04_idx ON reports_2009_04 USING btree (date);


--
-- Name: reports_2009_05_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_05_idx ON reports_2009_05 USING btree (date);


--
-- Name: reports_2009_06_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_06_idx ON reports_2009_06 USING btree (date);


--
-- Name: reports_2009_07_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_07_idx ON reports_2009_07 USING btree (date);


--
-- Name: reports_2009_08_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_08_idx ON reports_2009_08 USING btree (date);


--
-- Name: reports_2009_09_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_09_idx ON reports_2009_09 USING btree (date);


--
-- Name: reports_2009_10_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_10_idx ON reports_2009_10 USING btree (date);


--
-- Name: reports_2009_11_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_11_idx ON reports_2009_11 USING btree (date);


--
-- Name: reports_2009_12_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2009_12_idx ON reports_2009_12 USING btree (date);


--
-- Name: reports_2010_01_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_01_idx ON reports_2010_01 USING btree (date);


--
-- Name: reports_2010_02_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_02_idx ON reports_2010_02 USING btree (date);


--
-- Name: reports_2010_03_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_03_idx ON reports_2010_03 USING btree (date);


--
-- Name: reports_2010_04_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_04_idx ON reports_2010_04 USING btree (date);


--
-- Name: reports_2010_05_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_05_idx ON reports_2010_05 USING btree (date);


--
-- Name: reports_2010_06_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_06_idx ON reports_2010_06 USING btree (date);


--
-- Name: reports_2010_07_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_07_idx ON reports_2010_07 USING btree (date);


--
-- Name: reports_2010_08_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_08_idx ON reports_2010_08 USING btree (date);


--
-- Name: reports_2010_09_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_09_idx ON reports_2010_09 USING btree (date);


--
-- Name: reports_2010_10_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_10_idx ON reports_2010_10 USING btree (date);


--
-- Name: reports_2010_11_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_11_idx ON reports_2010_11 USING btree (date);


--
-- Name: reports_2010_12_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2010_12_idx ON reports_2010_12 USING btree (date);


--
-- Name: reports_2011_01_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_01_idx ON reports_2011_01 USING btree (date);


--
-- Name: reports_2011_02_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_02_idx ON reports_2011_02 USING btree (date);


--
-- Name: reports_2011_03_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_03_idx ON reports_2011_03 USING btree (date);


--
-- Name: reports_2011_04_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_04_idx ON reports_2011_04 USING btree (date);


--
-- Name: reports_2011_05_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_05_idx ON reports_2011_05 USING btree (date);


--
-- Name: reports_2011_06_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_06_idx ON reports_2011_06 USING btree (date);


--
-- Name: reports_2011_07_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_07_idx ON reports_2011_07 USING btree (date);


--
-- Name: reports_2011_08_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_08_idx ON reports_2011_08 USING btree (date);


--
-- Name: reports_2011_09_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_09_idx ON reports_2011_09 USING btree (date);


--
-- Name: reports_2011_10_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_10_idx ON reports_2011_10 USING btree (date);


--
-- Name: reports_2011_11_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_11_idx ON reports_2011_11 USING btree (date);


--
-- Name: reports_2011_12_idx; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX reports_2011_12_idx ON reports_2011_12 USING btree (date);


--
-- Name: top_crasher_lookup; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX top_crasher_lookup ON reports USING btree (product, version, build);


--
-- Name: url; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX url ON reports USING btree (url);


--
-- Name: ins_2007_01; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_01 AS ON INSERT TO reports WHERE ((new.date >= '2007-01-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-02-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_01 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_02; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_02 AS ON INSERT TO reports WHERE ((new.date >= '2007-02-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-03-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_02 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_03; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_03 AS ON INSERT TO reports WHERE ((new.date >= '2007-03-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-04-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_03 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_04; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_04 AS ON INSERT TO reports WHERE ((new.date >= '2007-04-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-05-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_04 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_05; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_05 AS ON INSERT TO reports WHERE ((new.date >= '2007-05-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-06-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_05 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_06; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_06 AS ON INSERT TO reports WHERE ((new.date >= '2007-06-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-07-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_06 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_07; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_07 AS ON INSERT TO reports WHERE ((new.date >= '2007-07-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-08-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_07 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_08; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_08 AS ON INSERT TO reports WHERE ((new.date >= '2007-08-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-09-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_08 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_09; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_09 AS ON INSERT TO reports WHERE ((new.date >= '2007-09-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-10-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_09 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_10; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_10 AS ON INSERT TO reports WHERE ((new.date >= '2007-10-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-11-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_10 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_11; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_11 AS ON INSERT TO reports WHERE ((new.date >= '2007-11-01 00:00:00'::timestamp without time zone) AND (new.date < '2007-12-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_11 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2007_12; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2007_12 AS ON INSERT TO reports WHERE ((new.date >= '2007-12-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-01-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2007_12 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_01; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_01 AS ON INSERT TO reports WHERE ((new.date >= '2008-01-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-02-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_01 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_02; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_02 AS ON INSERT TO reports WHERE ((new.date >= '2008-02-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-03-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_02 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_03; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_03 AS ON INSERT TO reports WHERE ((new.date >= '2008-03-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-04-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_03 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_04; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_04 AS ON INSERT TO reports WHERE ((new.date >= '2008-04-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-05-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_04 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_05; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_05 AS ON INSERT TO reports WHERE ((new.date >= '2008-05-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-06-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_05 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_06; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_06 AS ON INSERT TO reports WHERE ((new.date >= '2008-06-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-07-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_06 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_07; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_07 AS ON INSERT TO reports WHERE ((new.date >= '2008-07-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-08-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_07 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_08; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_08 AS ON INSERT TO reports WHERE ((new.date >= '2008-08-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-09-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_08 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_09; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_09 AS ON INSERT TO reports WHERE ((new.date >= '2008-09-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-10-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_09 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_10; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_10 AS ON INSERT TO reports WHERE ((new.date >= '2008-10-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-11-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_10 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_11; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_11 AS ON INSERT TO reports WHERE ((new.date >= '2008-11-01 00:00:00'::timestamp without time zone) AND (new.date < '2008-12-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_11 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2008_12; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2008_12 AS ON INSERT TO reports WHERE ((new.date >= '2008-12-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-01-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2008_12 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_01; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_01 AS ON INSERT TO reports WHERE ((new.date >= '2009-01-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-02-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_01 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_02; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_02 AS ON INSERT TO reports WHERE ((new.date >= '2009-02-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-03-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_02 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_03; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_03 AS ON INSERT TO reports WHERE ((new.date >= '2009-03-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-04-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_03 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_04; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_04 AS ON INSERT TO reports WHERE ((new.date >= '2009-04-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-05-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_04 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_05; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_05 AS ON INSERT TO reports WHERE ((new.date >= '2009-05-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-06-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_05 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_06; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_06 AS ON INSERT TO reports WHERE ((new.date >= '2009-06-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-07-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_06 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_07; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_07 AS ON INSERT TO reports WHERE ((new.date >= '2009-07-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-08-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_07 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_08; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_08 AS ON INSERT TO reports WHERE ((new.date >= '2009-08-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-09-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_08 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_09; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_09 AS ON INSERT TO reports WHERE ((new.date >= '2009-09-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-10-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_09 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_10; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_10 AS ON INSERT TO reports WHERE ((new.date >= '2009-10-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-11-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_10 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_11; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_11 AS ON INSERT TO reports WHERE ((new.date >= '2009-11-01 00:00:00'::timestamp without time zone) AND (new.date < '2009-12-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_11 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2009_12; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2009_12 AS ON INSERT TO reports WHERE ((new.date >= '2009-12-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-01-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2009_12 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_01; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_01 AS ON INSERT TO reports WHERE ((new.date >= '2010-01-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-02-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_01 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_02; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_02 AS ON INSERT TO reports WHERE ((new.date >= '2010-02-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-03-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_02 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_03; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_03 AS ON INSERT TO reports WHERE ((new.date >= '2010-03-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-04-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_03 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_04; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_04 AS ON INSERT TO reports WHERE ((new.date >= '2010-04-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-05-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_04 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_05; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_05 AS ON INSERT TO reports WHERE ((new.date >= '2010-05-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-06-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_05 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_06; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_06 AS ON INSERT TO reports WHERE ((new.date >= '2010-06-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-07-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_06 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_07; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_07 AS ON INSERT TO reports WHERE ((new.date >= '2010-07-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-08-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_07 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_08; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_08 AS ON INSERT TO reports WHERE ((new.date >= '2010-08-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-09-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_08 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_09; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_09 AS ON INSERT TO reports WHERE ((new.date >= '2010-09-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-10-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_09 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_10; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_10 AS ON INSERT TO reports WHERE ((new.date >= '2010-10-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-11-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_10 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_11; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_11 AS ON INSERT TO reports WHERE ((new.date >= '2010-11-01 00:00:00'::timestamp without time zone) AND (new.date < '2010-12-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_11 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2010_12; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2010_12 AS ON INSERT TO reports WHERE ((new.date >= '2010-12-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-01-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2010_12 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_01; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_01 AS ON INSERT TO reports WHERE ((new.date >= '2011-01-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-02-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_01 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_02; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_02 AS ON INSERT TO reports WHERE ((new.date >= '2011-02-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-03-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_02 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_03; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_03 AS ON INSERT TO reports WHERE ((new.date >= '2011-03-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-04-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_03 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_04; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_04 AS ON INSERT TO reports WHERE ((new.date >= '2011-04-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-05-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_04 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_05; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_05 AS ON INSERT TO reports WHERE ((new.date >= '2011-05-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-06-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_05 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_06; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_06 AS ON INSERT TO reports WHERE ((new.date >= '2011-06-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-07-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_06 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_07; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_07 AS ON INSERT TO reports WHERE ((new.date >= '2011-07-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-08-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_07 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_08; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_08 AS ON INSERT TO reports WHERE ((new.date >= '2011-08-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-09-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_08 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_09; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_09 AS ON INSERT TO reports WHERE ((new.date >= '2011-09-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-10-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_09 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_10; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_10 AS ON INSERT TO reports WHERE ((new.date >= '2011-10-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-11-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_10 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_11; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_11 AS ON INSERT TO reports WHERE ((new.date >= '2011-11-01 00:00:00'::timestamp without time zone) AND (new.date < '2011-12-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_11 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: ins_2011_12; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE ins_2011_12 AS ON INSERT TO reports WHERE ((new.date >= '2011-12-01 00:00:00'::timestamp without time zone) AND (new.date < '2012-01-01 00:00:00'::timestamp without time zone)) DO INSTEAD INSERT INTO reports_2011_12 (id, date, signature, last_crash, install_age, url, "comment", os_name, os_version, cpu_name, cpu_info, reason, address, product, version, build, platform, uuid) VALUES (new.id, new.date, new.signature, new.last_crash, new.install_age, new.url, new."comment", new.os_name, new.os_version, new.cpu_name, new.cpu_info, new.reason, new.address, new.product, new.version, new.build, new.platform, new.uuid);


--
-- Name: dumps_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dumps
    ADD CONSTRAINT dumps_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id);


--
-- Name: frames_fkey_report_id; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY frames
    ADD CONSTRAINT frames_fkey_report_id FOREIGN KEY (report_id) REFERENCES reports(id);


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--


