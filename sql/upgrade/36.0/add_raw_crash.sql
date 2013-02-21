BEGIN;

DROP TABLE IF EXISTS raw_crashes;
CREATE TABLE raw_crashes (
    uuid uuid NOT NULL,
    raw_crash JSON NOT NULL,
    date_processed timestamptz NOT NULL
);

CREATE UNIQUE INDEX raw_crashes_index ON raw_crashes(uuid);

-- add to report_partition_info

INSERT into report_partition_info
(table_name, build_order, keys, indexes, fkeys)
VALUES
('raw_crashes', 4, '{"uuid"}','{}', '{}');

COMMIT;
