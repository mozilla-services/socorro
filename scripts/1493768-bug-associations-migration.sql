--
-- Bug 1493768: bug associations data migration
--
-- Used for a single data migration October 2018. We can delete it after
-- using it in stage and prod.

BEGIN WORK;

-- Crontabber has a job that updates these tables. We lock the tables here
-- to prevent it from updating the data while we're migrating.
LOCK table bug_associations, crashstats_bugassociation;

-- Delete anything in the destination table. The assumption is that the
-- source table is completely up-to-date, so we can delete the data in the
-- destination table and insert everything from scratch.
DELETE FROM crashstats_bugassociation;

-- Copy everything from the source table to the destination one.
INSERT INTO crashstats_bugassociation (bug_id, signature)
    SELECT bug_id, signature
    FROM bug_associations;

-- Verify the two tables are the same.
SELECT count(*) as old_count FROM bug_associations;
SELECT count(*) as new_count FROM crashstats_bugassociation;

COMMIT WORK;
