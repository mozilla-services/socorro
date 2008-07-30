--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: PROCEDURAL LANGUAGE; Schema: -; Owner: 
--

CREATE PROCEDURAL LANGUAGE plpgsql;


SET search_path = public, pg_catalog;

--
-- Name: create_partition_rules(integer); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION create_partition_rules(partition integer) RETURNS void
    AS $_$
declare
    cur_partition integer := partition;
    tablename text;
    cmd text;
begin
    IF cur_partition IS NULL THEN
        SELECT INTO cur_partition get_latest_partition();
    END IF;

    tablename := 'reports_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_reports_partition AS
                  ON INSERT TO reports
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'frames_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_frames_partition AS
                  ON INSERT TO frames
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                  ARRAY [ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'modules_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_modules_partition AS
                  ON INSERT TO modules
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'extensions_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_extensions_partition AS
                  ON INSERT TO extensions
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;

    tablename := 'dumps_part' || cur_partition::text;
    cmd := subst('CREATE OR REPLACE RULE rule_dumps_partition AS
                  ON INSERT TO dumps
                  DO INSTEAD INSERT INTO $$ VALUES (NEW.*)',
                 ARRAY[ quote_ident(tablename) ]);
    execute cmd;
end;
$_$
    LANGUAGE plpgsql;


ALTER FUNCTION public.create_partition_rules(partition integer) OWNER TO postgres;

--
-- Name: drop_partition_rules(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION drop_partition_rules() RETURNS void
    AS $$
declare
    partition integer;
begin
    SELECT INTO partition get_latest_partition();
    IF partition IS NULL THEN
        RETURN;
    END IF;

    DROP RULE rule_reports_partition ON reports;
    DROP RULE rule_frames_partition ON frames;
    DROP RULE rule_modules_partition ON modules;
    DROP RULE rule_extensions_partition ON extensions;
    DROP RULE rule_dumps_partition ON dumps;
end;
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.drop_partition_rules() OWNER TO postgres;

--
-- Name: get_latest_partition(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION get_latest_partition() RETURNS integer
    AS $_$
declare
    partition integer;
begin
    SELECT INTO partition
        max(substring(tablename from '^reports_part(\\d+)$')::integer)
        FROM pg_tables WHERE tablename LIKE 'reports_part%';
    RETURN partition;
end;
$_$
    LANGUAGE plpgsql;


ALTER FUNCTION public.get_latest_partition() OWNER TO postgres;

--
-- Name: lock_for_changes(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION lock_for_changes() RETURNS void
    AS $$
declare
begin
    LOCK reports IN ROW EXCLUSIVE MODE;
    LOCK frames IN ROW EXCLUSIVE MODE;
    LOCK dumps IN ROW EXCLUSIVE MODE;
    LOCK modules IN ROW EXCLUSIVE MODE;
    LOCK extensions IN ROW EXCLUSIVE MODE;
end;
$$
    LANGUAGE plpgsql;


ALTER FUNCTION public.lock_for_changes() OWNER TO postgres;

--
-- Name: make_partition(); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION make_partition() RETURNS void
    AS $_$
declare
    new_partition integer;
    old_partition integer;
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
    PERFORM lock_for_changes();

    SELECT INTO old_partition get_latest_partition();

    IF old_partition IS NOT NULL THEN
        new_partition := old_partition + 1;

        old_tablename := 'reports_part' || old_partition::text;
        cmd := subst('SELECT max(id), min(date), max(date) FROM $$',
                     ARRAY[ quote_ident(old_tablename) ]);

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

        old_tablename := 'modules_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                         ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        old_tablename := 'extensions_part' || old_partition::text;
        cmd := subst('ALTER TABLE $$ ADD CHECK( report_id <= $$ )',
                     ARRAY[ quote_ident(old_tablename),
                            quote_literal(old_end_id) ]);
        execute cmd;

        start_id := old_end_id + 1;
    ELSE
        new_partition := 1;
    END IF;

    tablename := 'reports_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    PRIMARY KEY(id),
                    UNIQUE(uuid),
                    CHECK(id >= $$)
                  ) INHERITS (reports)',
                 ARRAY[ quote_ident(tablename),
                        quote_literal(start_id) ]);
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
                    FOREIGN KEY(report_id) REFERENCES $$ (id) ON DELETE CASCADE
                  ) INHERITS (frames)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'modules_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id, module_key),
                    FOREIGN KEY(report_id) REFERENCES $$ (id) ON DELETE CASCADE
                  ) INHERITS (modules)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'extensions_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id, extension_key),
                    FOREIGN KEY(report_id) REFERENCES $$ (id) ON DELETE CASCADE
                  ) INHERITS (extensions)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    objname := 'dumps_part' || new_partition::text;
    cmd := subst('CREATE TABLE $$ (
                    CHECK(report_id >= $$),
                    PRIMARY KEY(report_id),
                    FOREIGN KEY(report_id) REFERENCES $$ (id) ON DELETE CASCADE
                  ) INHERITS (dumps)',
                 ARRAY[ quote_ident(objname),
                        quote_literal(start_id),
                        quote_ident(tablename) ]);
    execute cmd;

    PERFORM create_partition_rules(new_partition);
end;
$_$
    LANGUAGE plpgsql;


ALTER FUNCTION public.make_partition() OWNER TO postgres;

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
-- Name: branches; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE branches (
    product character varying(30) NOT NULL,
    version character varying(16) NOT NULL,
    branch character varying(24) NOT NULL
);


ALTER TABLE public.branches OWNER TO postgres;

--
-- Name: dumps; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE dumps (
    report_id integer NOT NULL,
    truncated boolean,
    data text
);


ALTER TABLE public.dumps OWNER TO postgres;

--
-- Name: dumps_part1; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE dumps_part1 (CONSTRAINT dumps_part1_report_id_check CHECK ((report_id >= 0))
)
INHERITS (dumps);


ALTER TABLE public.dumps_part1 OWNER TO postgres;

--
-- Name: extensions; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE extensions (
    report_id integer NOT NULL,
    extension_key integer NOT NULL,
    extension_id character varying(100) NOT NULL,
    extension_version character varying(16)
);


ALTER TABLE public.extensions OWNER TO postgres;

--
-- Name: extensions_part1; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE extensions_part1 (CONSTRAINT extensions_part1_report_id_check CHECK ((report_id >= 0))
)
INHERITS (extensions);


ALTER TABLE public.extensions_part1 OWNER TO postgres;

--
-- Name: frames; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE frames (
    report_id integer NOT NULL,
    frame_num integer NOT NULL,
    signature character varying(255)
);


ALTER TABLE public.frames OWNER TO postgres;

--
-- Name: frames_part1; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE frames_part1 (CONSTRAINT frames_part1_report_id_check CHECK ((report_id >= 0))
)
INHERITS (frames);


ALTER TABLE public.frames_part1 OWNER TO postgres;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE jobs (
    id integer NOT NULL,
    pathname character varying(1024) NOT NULL,
    uuid character varying(50) NOT NULL,
    "owner" integer,
    priority integer,
    queueddatetime timestamp without time zone,
    starteddatetime timestamp without time zone,
    completeddatetime timestamp without time zone,
    success boolean,
    message text
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- Name: modules; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE modules (
    report_id integer NOT NULL,
    module_key integer NOT NULL,
    filename character varying(40) NOT NULL,
    debug_id character varying(40),
    module_version character varying(15),
    debug_filename character varying(40)
);


ALTER TABLE public.modules OWNER TO postgres;

--
-- Name: modules_part1; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE modules_part1 (CONSTRAINT modules_part1_report_id_check CHECK ((report_id >= 0))
)
INHERITS (modules);


ALTER TABLE public.modules_part1 OWNER TO postgres;

--
-- Name: priorityjobs; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE priorityjobs (
    uuid character varying(50) NOT NULL
);


ALTER TABLE public.priorityjobs OWNER TO postgres;

--
-- Name: processors; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE processors (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    startdatetime timestamp without time zone NOT NULL,
    lastseendatetime timestamp without time zone
);


ALTER TABLE public.processors OWNER TO postgres;

--
-- Name: reports; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports (
    id integer NOT NULL,
    date timestamp with time zone NOT NULL,
    date_processed timestamp without time zone NOT NULL,
    uuid character varying(50) NOT NULL,
    product character varying(30),
    version character varying(16),
    build character varying(30),
    signature character varying(255),
    url character varying(255),
    install_age integer,
    last_crash integer,
    uptime integer,
    comments character varying(500),
    cpu_name character varying(100),
    cpu_info character varying(100),
    reason character varying(255),
    address character varying(20),
    os_name character varying(100),
    os_version character varying(100),
    email character varying(100),
    build_date timestamp without time zone,
    user_id character varying(50),
    starteddatetime timestamp without time zone,
    completeddatetime timestamp without time zone,
    success boolean,
    message text,
    truncated boolean
);


ALTER TABLE public.reports OWNER TO postgres;

--
-- Name: reports_part1; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE reports_part1 (CONSTRAINT reports_part1_id_check CHECK ((id >= 0))
)
INHERITS (reports);


ALTER TABLE public.reports_part1 OWNER TO postgres;

--
-- Name: seq_reports_id; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE seq_reports_id
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.seq_reports_id OWNER TO postgres;

--
-- Name: topcrashers; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE topcrashers (
    id serial NOT NULL,
    signature character varying(255) NOT NULL,
    version character varying(30) NOT NULL,
    product character varying(30) NOT NULL,
    build character varying(30) NOT NULL,
    total integer,
    win integer,
    mac integer,
    linux integer,
    rank integer,
    last_rank integer,
    trend character varying(30),
    uptime real,
    users integer,
    last_updated timestamp without time zone
);


ALTER TABLE public.topcrashers OWNER TO postgres;

--
-- Name: branches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (product, version);


--
-- Name: dumps_part1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY dumps_part1
    ADD CONSTRAINT dumps_part1_pkey PRIMARY KEY (report_id);


--
-- Name: dumps_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY dumps
    ADD CONSTRAINT dumps_pkey PRIMARY KEY (report_id);


--
-- Name: extensions_part1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY extensions_part1
    ADD CONSTRAINT extensions_part1_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: extensions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY extensions
    ADD CONSTRAINT extensions_pkey PRIMARY KEY (report_id, extension_key);


--
-- Name: frames_part1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY frames_part1
    ADD CONSTRAINT frames_part1_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: frames_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY frames
    ADD CONSTRAINT frames_pkey PRIMARY KEY (report_id, frame_num);


--
-- Name: jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: modules_part1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY modules_part1
    ADD CONSTRAINT modules_part1_pkey PRIMARY KEY (report_id, module_key);


--
-- Name: modules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY modules
    ADD CONSTRAINT modules_pkey PRIMARY KEY (report_id, module_key);


--
-- Name: priorityjobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY priorityjobs
    ADD CONSTRAINT priorityjobs_pkey PRIMARY KEY (uuid);


--
-- Name: processors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY processors
    ADD CONSTRAINT processors_pkey PRIMARY KEY (id);


--
-- Name: reports_part1_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY reports_part1
    ADD CONSTRAINT reports_part1_pkey PRIMARY KEY (id);


--
-- Name: reports_part1_uuid_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY reports_part1
    ADD CONSTRAINT reports_part1_uuid_key UNIQUE (uuid);


--
-- Name: reports_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY reports
    ADD CONSTRAINT reports_pkey PRIMARY KEY (id);


--
-- Name: topcrashers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY topcrashers
    ADD CONSTRAINT topcrashers_pkey PRIMARY KEY (id);


--
-- Name: idx_reports_date; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_reports_date ON reports USING btree (date, product, version, build);


--
-- Name: idx_reports_part1_date; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_reports_part1_date ON reports_part1 USING btree (date, product, version, build);


--
-- Name: ix_jobs_uuid; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX ix_jobs_uuid ON jobs USING btree (uuid);


--
-- Name: ix_reports_signature; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_reports_signature ON reports USING btree (signature);


--
-- Name: ix_reports_url; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX ix_reports_url ON reports USING btree (url);


--
-- Name: ix_reports_uuid; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX ix_reports_uuid ON reports USING btree (uuid);


--
-- Name: rule_dumps_partition; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE rule_dumps_partition AS ON INSERT TO dumps DO INSTEAD INSERT INTO dumps_part1 (report_id, truncated, data) VALUES (new.report_id, new.truncated, new.data);


--
-- Name: rule_extensions_partition; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE rule_extensions_partition AS ON INSERT TO extensions DO INSTEAD INSERT INTO extensions_part1 (report_id, extension_key, extension_id, extension_version) VALUES (new.report_id, new.extension_key, new.extension_id, new.extension_version);


--
-- Name: rule_frames_partition; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE rule_frames_partition AS ON INSERT TO frames DO INSTEAD INSERT INTO frames_part1 (report_id, frame_num, signature) VALUES (new.report_id, new.frame_num, new.signature);


--
-- Name: rule_modules_partition; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE rule_modules_partition AS ON INSERT TO modules DO INSTEAD INSERT INTO modules_part1 (report_id, module_key, filename, debug_id, module_version, debug_filename) VALUES (new.report_id, new.module_key, new.filename, new.debug_id, new.module_version, new.debug_filename);


--
-- Name: rule_reports_partition; Type: RULE; Schema: public; Owner: postgres
--

CREATE RULE rule_reports_partition AS ON INSERT TO reports DO INSTEAD INSERT INTO reports_part1 (id, date, date_processed, uuid, product, version, build, signature, url, install_age, last_crash, uptime, comments, cpu_name, cpu_info, reason, address, os_name, os_version, email, build_date, user_id, starteddatetime, completeddatetime, success, message, truncated) VALUES (new.id, new.date, new.date_processed, new.uuid, new.product, new.version, new.build, new.signature, new.url, new.install_age, new.last_crash, new.uptime, new.comments, new.cpu_name, new.cpu_info, new.reason, new.address, new.os_name, new.os_version, new.email, new.build_date, new.user_id, new.starteddatetime, new.completeddatetime, new.success, new.message, new.truncated);


--
-- Name: dumps_part1_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dumps_part1
    ADD CONSTRAINT dumps_part1_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_part1(id) ON DELETE CASCADE;


--
-- Name: dumps_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY dumps
    ADD CONSTRAINT dumps_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE;


--
-- Name: extensions_part1_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY extensions_part1
    ADD CONSTRAINT extensions_part1_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_part1(id) ON DELETE CASCADE;


--
-- Name: extensions_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY extensions
    ADD CONSTRAINT extensions_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE;


--
-- Name: frames_part1_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY frames_part1
    ADD CONSTRAINT frames_part1_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_part1(id) ON DELETE CASCADE;


--
-- Name: frames_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY frames
    ADD CONSTRAINT frames_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE;


--
-- Name: jobs_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_owner_fkey FOREIGN KEY ("owner") REFERENCES processors(id);


--
-- Name: modules_part1_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY modules_part1
    ADD CONSTRAINT modules_part1_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports_part1(id) ON DELETE CASCADE;


--
-- Name: modules_report_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY modules
    ADD CONSTRAINT modules_report_id_fkey FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

