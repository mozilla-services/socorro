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
    last_crash integer,
    install_age integer,
    url character varying,
    comments text,
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
-- Name: top_crasher_lookup; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX top_crasher_lookup ON reports USING btree (product, version, build);


--
-- Name: url; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX url ON reports USING btree (url);


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


