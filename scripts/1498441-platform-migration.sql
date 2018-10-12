--
-- Bug 1498441: platform data migration
--
-- Used for a single data migration October 2018. We can delete it after
-- using it in stage and prod.

BEGIN WORK;

-- Crontabber has a job that updates these tables. We lock the tables here
-- to prevent it from updating the data while we're migrating.
LOCK table os_names, crashstats_platform;

-- Delete anything in the destination table. The assumption is that the
-- source table is completely up-to-date, so we can delete the data in the
-- destination table and insert everything from scratch.
DELETE FROM crashstats_platform;

-- Copy everything from the source to the destination.
INSERT INTO crashstats_platform (name, short_name)
    SELECT os_name, os_short_name
    FROM os_names;

-- Verify the two tables are similar. Note that they won't be the same since
-- we dropped some data in the migration.
SELECT count(*) FROM os_names;
SELECT count(*) FROM crashstats_platform;

COMMIT WORK;
