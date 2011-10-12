
BEGIN;
ALTER TABLE releases_raw ADD COLUMN repository CITEXT;
UPDATE releases_raw SET repository = 'mozilla-release' WHERE repository IS NULL;
ALTER TABLE releases_raw ALTER COLUMN repository SET DEFAULT 'mozilla-release';
ALTER TABLE releases_raw DROP CONSTRAINT release_raw_key;
ALTER TABLE releases_raw 
	ADD CONSTRAINT release_raw_key PRIMARY KEY ( product_name, version, build_type, build_id, platform, repository);
END;

CREATE INDEX releases_raw_date ON releases_raw((build_date(build_id)));