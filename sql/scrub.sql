BEGIN;
-- scrub user data for development purposes
ALTER TABLE reports DROP COLUMN url, DROP COLUMN email;
ALTER TABLE reports ADD COLUMN url TEXT, ADD COLUMN email TEXT;
ALTER TABLE reports_user_info DROP COLUMN url, DROP COLUMN email;
ALTER TABLE reports_user_info ADD COLUMN url TEXT, ADD COLUMN email CITEXT;
ALTER TABLE email_contacts DROP COLUMN email;
ALTER TABLE email_contacts ADD COLUMN email TEXT;
TRUNCATE urldims;

-- remove anything unnecessary
TRUNCATE sessions CASCADE;
TRUNCATE bugs CASCADE;
TRUNCATE status CASCADE;
COMMIT;
