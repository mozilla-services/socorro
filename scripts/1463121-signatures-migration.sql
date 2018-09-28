--
-- Bug 1461321: signatures data migration

-- Delete anything in the table. The assumption is that the old table
-- has all the data in it, so we can delete the data in the new table
-- and copy everything from scratch.
DELETE FROM crashstats_signature;

-- Copy everything from the old table to the new one. The one twist
-- is that the new table has a "first_date" column and the old one
-- has a "first_report" column.
INSERT INTO crashstats_signature (signature, first_build, first_date)
    SELECT signature, first_build, first_report
    FROM signatures
    WHERE
        signature IS NOT NULL
        AND first_build IS NOT NULL
        AND first_report IS NOT NULL;
