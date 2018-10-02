--
-- Bug 1461321: signatures data migration
--
-- Used for a single data migration October 2018. We can delete it after
-- using it in stage and prod.

BEGIN WORK;

-- Crontabber has a job that updates these tables. We lock the tables here
-- to prevent it from updating the data while we're migrating.
LOCK table signatures, crashstats_signature;

-- Delete anything in the destination table. The assumption is that the
-- source table is completely up-to-date, so we can delete the data in the
-- destination table and insert everything from scratch.
DELETE FROM crashstats_signature;

-- Copy everything from the source table to the destination one with some
-- caveats:
--
-- 1. the destination table has a "first_date" column and the source one has
--    a "first_report" column
-- 2. in prod, we have two rows with the same signature violating the unique
--    constraint, so we drop that data
-- 3. in stage and prod, there are rows with NULL in either first_build or
--    which is junk data, so we drop that, too
INSERT INTO crashstats_signature (signature, first_build, first_date)
    SELECT signature, first_build, first_report
    FROM signatures
    WHERE
        signature IS NOT NULL
        AND signature != 'java.lang.NoSuchFieldError: @rawableCorners at android.graphics.drawable.GradientDrawable.inflate(GradientDrawable.java)'
        AND first_build IS NOT NULL
        AND first_report IS NOT NULL;

-- Verify the two tables are similar. Note that they won't be the same since
-- we dropped some data in the migration.
SELECT count(*) FROM signatures;
SELECT count(*) FROM crashstats_signature;

COMMIT WORK;
