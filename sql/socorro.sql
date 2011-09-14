--
-- PostgreSQL database dump
--

SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: branches; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE branches (
    product character varying(30) NOT NULL,
    version character varying(16) NOT NULL,
    branch character varying(24) NOT NULL
);


ALTER TABLE public.branches OWNER TO breakpad_rw;

--
-- Name: dumps; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE dumps (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    data text
);


ALTER TABLE public.dumps OWNER TO breakpad_rw;

--
-- Name: extensions; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE extensions (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    extension_key integer NOT NULL,
    extension_id character varying(100) NOT NULL,
    extension_version character varying(16)
);


ALTER TABLE public.extensions OWNER TO breakpad_rw;

--
-- Name: frames; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE frames (
    report_id integer NOT NULL,
    date_processed timestamp without time zone,
    frame_num integer NOT NULL,
    signature character varying(255)
);


ALTER TABLE public.frames OWNER TO breakpad_rw;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE jobs (
    id integer NOT NULL,
    pathname character varying(1024) NOT NULL,
    uuid character varying(50) NOT NULL,
    owner integer,
    priority integer DEFAULT 0,
    queueddatetime timestamp without time zone,
    starteddatetime timestamp without time zone,
    completeddatetime timestamp without time zone,
    success boolean,
    message text
);


ALTER TABLE public.jobs OWNER TO breakpad_rw;

--
-- Name: mtbfconfig; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE mtbfconfig (
    id integer NOT NULL,
    productdims_id integer,
    start_dt date,
    end_dt date
);


ALTER TABLE public.mtbfconfig OWNER TO breakpad_rw;

--
-- Name: mtbffacts; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE mtbffacts (
    id integer NOT NULL,
    avg_seconds integer NOT NULL,
    report_count integer NOT NULL,
    unique_users integer NOT NULL,
    day date,
    productdims_id integer
);


ALTER TABLE public.mtbffacts OWNER TO breakpad_rw;

--
-- Name: priorityjobs; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE priorityjobs (
    uuid character varying(255) NOT NULL
);


ALTER TABLE public.priorityjobs OWNER TO breakpad_rw;

--
-- Name: processors; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE processors (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    startdatetime timestamp without time zone NOT NULL,
    lastseendatetime timestamp without time zone
);


ALTER TABLE public.processors OWNER TO breakpad_rw;

--
-- Name: productdims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE productdims (
    id integer NOT NULL,
    product character varying(30) NOT NULL,
    version character varying(16) NOT NULL,
    os_name character varying(100),
    release character varying(50) NOT NULL
);


ALTER TABLE public.productdims OWNER TO breakpad_rw;

--
-- Name: reports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE reports (
    id integer NOT NULL,
    client_crash_date timestamp with time zone,
    date_processed timestamp without time zone,
    uuid character varying(50) NOT NULL,
    product character varying(30),
    version character varying(16),
    build character varying(30),
    signature character varying(255),
    url character varying(255),
    install_age integer,
    last_crash integer,
    uptime integer,
    cpu_name character varying(100),
    cpu_info character varying(100),
    reason character varying(255),
    address character varying(20),
    os_name character varying(100),
    os_version character varying(100),
    email character varying(100),
    build_date timestamp without time zone,
    user_id character varying(50),
    started_datetime timestamp without time zone,
    completed_datetime timestamp without time zone,
    success boolean,
    truncated boolean,
    processor_notes text,
    user_comments character varying(1024),
    app_notes character varying(1024),
    distributor character varying(20),
    distributor_version character varying(20)
);


ALTER TABLE public.reports OWNER TO breakpad_rw;

--
-- Name: reports_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE reports_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.reports_id_seq OWNER TO breakpad_rw;

--
-- Name: reports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE reports_id_seq OWNED BY reports.id;


--
-- Name: reports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('reports_id_seq', 2027, true);

--
-- Name: server_status; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE server_status (
    id integer NOT NULL,
    date_recently_completed timestamp without time zone,
    date_oldest_job_queued timestamp without time zone,
    avg_process_sec real,
    avg_wait_sec real,
    waiting_job_count integer NOT NULL,
    processors_count integer NOT NULL,
    date_created timestamp without time zone NOT NULL
);


ALTER TABLE public.server_status OWNER TO breakpad_rw;

--
-- Name: signaturedims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE signaturedims (
    id integer NOT NULL,
    signature character varying(255) NOT NULL
);


ALTER TABLE public.signaturedims OWNER TO breakpad_rw;

--
-- Name: tcbyurlconfig; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE tcbyurlconfig (
    id integer NOT NULL,
    productdims_id integer,
    enabled boolean
);


ALTER TABLE public.tcbyurlconfig OWNER TO breakpad_rw;

--
-- Name: topcrashers; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE topcrashers (
    id integer NOT NULL,
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


ALTER TABLE public.topcrashers OWNER TO breakpad_rw;

SET default_with_oids = true;

--
-- Name: topcrashurlfacts; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE topcrashurlfacts (
    id integer NOT NULL,
    count integer NOT NULL,
    rank integer,
    day date NOT NULL,
    productdims_id integer,
    urldims_id integer,
    signaturedims_id integer
);


ALTER TABLE public.topcrashurlfacts OWNER TO breakpad_rw;

SET default_with_oids = false;

--
-- Name: topcrashurlfactsreports; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE topcrashurlfactsreports (
    id integer NOT NULL,
    uuid character varying(50) NOT NULL,
    comments character varying(500),
    topcrashurlfacts_id integer
);


ALTER TABLE public.topcrashurlfactsreports OWNER TO breakpad_rw;

--
-- Name: urldims; Type: TABLE; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE TABLE urldims (
    id integer NOT NULL,
    domain character varying(255) NOT NULL,
    url character varying(255) NOT NULL
);


ALTER TABLE public.urldims OWNER TO breakpad_rw;

--
-- Name: jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE jobs_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.jobs_id_seq OWNER TO breakpad_rw;

--
-- Name: jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE jobs_id_seq OWNED BY jobs.id;


--
-- Name: jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('jobs_id_seq', 252058, true);


--
-- Name: mtbfconfig_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE mtbfconfig_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.mtbfconfig_id_seq OWNER TO breakpad_rw;

--
-- Name: mtbfconfig_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE mtbfconfig_id_seq OWNED BY mtbfconfig.id;


--
-- Name: mtbfconfig_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('mtbfconfig_id_seq', 30, true);


--
-- Name: mtbffacts_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE mtbffacts_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.mtbffacts_id_seq OWNER TO breakpad_rw;

--
-- Name: mtbffacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE mtbffacts_id_seq OWNED BY mtbffacts.id;


--
-- Name: mtbffacts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('mtbffacts_id_seq', 27, true);


--
-- Name: processors_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE processors_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.processors_id_seq OWNER TO breakpad_rw;

--
-- Name: processors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE processors_id_seq OWNED BY processors.id;


--
-- Name: processors_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('processors_id_seq', 360, true);


--
-- Name: productdims_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE productdims_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.productdims_id_seq OWNER TO breakpad_rw;

--
-- Name: productdims_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE productdims_id_seq OWNED BY productdims.id;


--
-- Name: productdims_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('productdims_id_seq', 39, true);


--
-- Name: seq_reports_id; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE seq_reports_id
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.seq_reports_id OWNER TO breakpad_rw;

--
-- Name: seq_reports_id; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('seq_reports_id', 68836, true);


--
-- Name: server_status_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE server_status_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.server_status_id_seq OWNER TO breakpad_rw;

--
-- Name: server_status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE server_status_id_seq OWNED BY server_status.id;


--
-- Name: server_status_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('server_status_id_seq', 2, true);


--
-- Name: signaturedims_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE signaturedims_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.signaturedims_id_seq OWNER TO breakpad_rw;

--
-- Name: signaturedims_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE signaturedims_id_seq OWNED BY signaturedims.id;


--
-- Name: signaturedims_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('signaturedims_id_seq', 32, true);


--
-- Name: tcbyurlconfig_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE tcbyurlconfig_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.tcbyurlconfig_id_seq OWNER TO breakpad_rw;

--
-- Name: tcbyurlconfig_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE tcbyurlconfig_id_seq OWNED BY tcbyurlconfig.id;


--
-- Name: tcbyurlconfig_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('tcbyurlconfig_id_seq', 4, true);


--
-- Name: topcrashers_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE topcrashers_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.topcrashers_id_seq OWNER TO breakpad_rw;

--
-- Name: topcrashers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE topcrashers_id_seq OWNED BY topcrashers.id;


--
-- Name: topcrashers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('topcrashers_id_seq', 211, true);


--
-- Name: topcrashurlfacts_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE topcrashurlfacts_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.topcrashurlfacts_id_seq OWNER TO breakpad_rw;

--
-- Name: topcrashurlfacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE topcrashurlfacts_id_seq OWNED BY topcrashurlfacts.id;


--
-- Name: topcrashurlfacts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('topcrashurlfacts_id_seq', 410, true);


--
-- Name: topcrashurlfactsreports_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE topcrashurlfactsreports_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.topcrashurlfactsreports_id_seq OWNER TO breakpad_rw;

--
-- Name: topcrashurlfactsreports_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE topcrashurlfactsreports_id_seq OWNED BY topcrashurlfactsreports.id;


--
-- Name: topcrashurlfactsreports_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('topcrashurlfactsreports_id_seq', 1, false);


--
-- Name: urldims_id_seq; Type: SEQUENCE; Schema: public; Owner: breakpad_rw
--

CREATE SEQUENCE urldims_id_seq
    INCREMENT BY 1
    NO MAXVALUE
    NO MINVALUE
    CACHE 1;


ALTER TABLE public.urldims_id_seq OWNER TO breakpad_rw;

--
-- Name: urldims_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: breakpad_rw
--

ALTER SEQUENCE urldims_id_seq OWNED BY urldims.id;


--
-- Name: urldims_id_seq; Type: SEQUENCE SET; Schema: public; Owner: breakpad_rw
--

SELECT pg_catalog.setval('urldims_id_seq', 274, true);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE mtbfconfig ALTER COLUMN id SET DEFAULT nextval('mtbfconfig_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE mtbffacts ALTER COLUMN id SET DEFAULT nextval('mtbffacts_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE processors ALTER COLUMN id SET DEFAULT nextval('processors_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE productdims ALTER COLUMN id SET DEFAULT nextval('productdims_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE reports ALTER COLUMN id SET DEFAULT nextval('reports_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE server_status ALTER COLUMN id SET DEFAULT nextval('server_status_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE signaturedims ALTER COLUMN id SET DEFAULT nextval('signaturedims_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE tcbyurlconfig ALTER COLUMN id SET DEFAULT nextval('tcbyurlconfig_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE topcrashers ALTER COLUMN id SET DEFAULT nextval('topcrashers_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE topcrashurlfacts ALTER COLUMN id SET DEFAULT nextval('topcrashurlfacts_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE topcrashurlfactsreports ALTER COLUMN id SET DEFAULT nextval('topcrashurlfactsreports_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE urldims ALTER COLUMN id SET DEFAULT nextval('urldims_id_seq'::regclass);


--
-- Name: branches_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY branches
    ADD CONSTRAINT branches_pkey PRIMARY KEY (product, version);


--
-- Name: jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: jobs_uuid_key; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_uuid_key UNIQUE (uuid);


--
-- Name: mtbfconfig_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY mtbfconfig
    ADD CONSTRAINT mtbfconfig_pkey PRIMARY KEY (id);


--
-- Name: mtbffacts_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY mtbffacts
    ADD CONSTRAINT mtbffacts_pkey PRIMARY KEY (id);



--
-- Name: priorityjobs_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY priorityjobs
    ADD CONSTRAINT priorityjobs_pkey PRIMARY KEY (uuid);


--
-- Name: processors_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY processors
    ADD CONSTRAINT processors_pkey PRIMARY KEY (id);


--
-- Name: productdims_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY productdims
    ADD CONSTRAINT productdims_pkey PRIMARY KEY (id);

--
-- Name: server_status_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY server_status
    ADD CONSTRAINT server_status_pkey PRIMARY KEY (id);


--
-- Name: signaturedims_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY signaturedims
    ADD CONSTRAINT signaturedims_pkey PRIMARY KEY (id);


--
-- Name: tcbyurlconfig_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY tcbyurlconfig
    ADD CONSTRAINT tcbyurlconfig_pkey PRIMARY KEY (id);


--
-- Name: topcrashers_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY topcrashers
    ADD CONSTRAINT topcrashers_pkey PRIMARY KEY (id);


--
-- Name: topcrashurlfacts_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY topcrashurlfacts
    ADD CONSTRAINT topcrashurlfacts_pkey PRIMARY KEY (id);


--
-- Name: topcrashurlfactsreports_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY topcrashurlfactsreports
    ADD CONSTRAINT topcrashurlfactsreports_pkey PRIMARY KEY (id);


--
-- Name: urldims_pkey; Type: CONSTRAINT; Schema: public; Owner: breakpad_rw; Tablespace:
--

ALTER TABLE ONLY urldims
    ADD CONSTRAINT urldims_pkey PRIMARY KEY (id);

--
-- Name: idx_jobs_completed_queue_datetime; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX idx_jobs_completed_queue_datetime ON jobs USING btree (completeddatetime, queueddatetime);


--
-- Name: idx_processor_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX idx_processor_name ON processors USING btree (name);


--
-- Name: idx_server_status_date; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX idx_server_status_date ON server_status USING btree (date_created, id);


--
-- Name: jobs_completeddatetime_queueddatetime_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX jobs_completeddatetime_queueddatetime_key ON jobs USING btree (completeddatetime, queueddatetime);


--
-- Name: jobs_owner_started; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX jobs_owner_started ON jobs USING btree (owner, starteddatetime);


--
-- Name: jobs_owner_starteddatetime_priority_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX jobs_owner_starteddatetime_priority_key ON jobs USING btree (owner, starteddatetime, priority DESC);


--
-- Name: jobs_success_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX jobs_success_key ON jobs USING btree (success);


--
-- Name: mtbfconfig_end_dt_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX mtbfconfig_end_dt_key ON mtbfconfig USING btree (end_dt);


--
-- Name: mtbfconfig_start_dt_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX mtbfconfig_start_dt_key ON mtbfconfig USING btree (start_dt);


--
-- Name: mtbffacts_day_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX mtbffacts_day_key ON mtbffacts USING btree (day);


--
-- Name: mtbffacts_product_id_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX mtbffacts_product_id_key ON mtbffacts USING btree (productdims_id);


--
-- Name: os_name; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX os_name ON reports USING btree (os_name);


--
-- Name: productdims_product_version_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX productdims_product_version_key ON productdims USING btree (product, version);


--
-- Name: productdims_product_version_os_name_release_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX productdims_product_version_os_name_release_key ON productdims USING btree (product, version, release, os_name);

--
-- Name: signaturedims_signature_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX signaturedims_signature_key ON signaturedims USING btree (signature);


--
-- Name: topcrashurlfacts_count_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfacts_count_key ON topcrashurlfacts USING btree (count);


--
-- Name: topcrashurlfacts_day_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfacts_day_key ON topcrashurlfacts USING btree (day);


--
-- Name: topcrashurlfacts_productdims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfacts_productdims_key ON topcrashurlfacts USING btree (productdims_id);


--
-- Name: topcrashurlfacts_signaturedims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfacts_signaturedims_key ON topcrashurlfacts USING btree (signaturedims_id);


--
-- Name: topcrashurlfacts_urldims_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfacts_urldims_key ON topcrashurlfacts USING btree (urldims_id);


--
-- Name: topcrashurlfactsreports_topcrashurlfacts_id_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE INDEX topcrashurlfactsreports_topcrashurlfacts_id_key ON topcrashurlfactsreports USING btree (topcrashurlfacts_id);


--
-- Name: urldims_url_domain_key; Type: INDEX; Schema: public; Owner: breakpad_rw; Tablespace:
--

CREATE UNIQUE INDEX urldims_url_domain_key ON urldims USING btree (url, domain);


--
-- Name: jobs_owner_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_owner_fkey FOREIGN KEY (owner) REFERENCES processors(id) ON DELETE CASCADE;


--
-- Name: mtbfconfig_productdims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY mtbfconfig
    ADD CONSTRAINT mtbfconfig_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);


--
-- Name: mtbffacts_productdims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY mtbffacts
    ADD CONSTRAINT mtbffacts_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);


--
-- Name: tcbyurlconfig_productdims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY tcbyurlconfig
    ADD CONSTRAINT tcbyurlconfig_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);


--
-- Name: topcrashurlfacts_productdims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY topcrashurlfacts
    ADD CONSTRAINT topcrashurlfacts_productdims_id_fkey FOREIGN KEY (productdims_id) REFERENCES productdims(id);


--
-- Name: topcrashurlfacts_signaturedims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY topcrashurlfacts
    ADD CONSTRAINT topcrashurlfacts_signaturedims_id_fkey FOREIGN KEY (signaturedims_id) REFERENCES signaturedims(id);


--
-- Name: topcrashurlfacts_urldims_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY topcrashurlfacts
    ADD CONSTRAINT topcrashurlfacts_urldims_id_fkey FOREIGN KEY (urldims_id) REFERENCES urldims(id);


--
-- Name: topcrashurlfactsreports_topcrashurlfacts_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: breakpad_rw
--

ALTER TABLE ONLY topcrashurlfactsreports
    ADD CONSTRAINT topcrashurlfactsreports_topcrashurlfacts_id_fkey FOREIGN KEY (topcrashurlfacts_id) REFERENCES topcrashurlfacts(id) ON DELETE CASCADE;

--
-- PostgreSQL database dump complete
--

