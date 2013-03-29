CREATE VIEW performance_check_1 AS
    SELECT sum(tcbs.report_count) AS sum FROM tcbs WHERE ((tcbs.report_date >= (('now'::text)::date - 7)) AND (tcbs.report_date <= ('now'::text)::date))
;
