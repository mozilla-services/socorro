CREATE DOMAIN major_version AS text
	CONSTRAINT major_version_check CHECK ((VALUE ~ '^\d+\.\d+'::text))
;
