

CREATE VIEW performance_check_1 AS
    SELECT sum(report_count) FROM tcbs
    WHERE report_date BETWEEN ( current_date - 7 ) and current_date;


ALTER TABLE public.performance_check_1 OWNER TO ganglia;

--
-- Name: performance_check_1; Type: ACL; Schema: public; Owner: ganglia
--

REVOKE ALL ON TABLE performance_check_1 FROM PUBLIC;
REVOKE ALL ON TABLE performance_check_1 FROM ganglia;
GRANT ALL ON TABLE performance_check_1 TO ganglia;
GRANT SELECT ON TABLE performance_check_1 TO breakpad;
GRANT SELECT ON TABLE performance_check_1 TO breakpad_ro;
GRANT ALL ON TABLE performance_check_1 TO monitor;


