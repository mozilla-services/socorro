CREATE FUNCTION create_os_version_string(osname citext, major integer, minor integer) RETURNS citext
    LANGUAGE plpgsql STABLE STRICT
    AS $$
DECLARE winversion CITEXT;
BEGIN
	-- small function which produces a user-friendly
	-- string for the operating system and version
	-- if windows, look it up in windows_versions
	IF osname = 'Windows' THEN
		SELECT windows_version_name INTO winversion
		FROM windows_versions
		WHERE major_version = major AND minor_version = minor;
		IF NOT FOUND THEN
			RETURN 'Windows Unknown';
		ELSE
			RETURN winversion;
		END IF;
	ELSEIF osname = 'Mac OS X' THEN
	-- if mac, then concatinate unless the numbers are impossible
		IF major BETWEEN 10 and 11 AND minor BETWEEN 0 and 20 THEN
			RETURN 'OS X ' || major || '.' || minor;
		ELSE
			RETURN 'OS X Unknown';
		END IF;
	ELSE
	-- for other oses, just use the OS name
		RETURN osname;
	END IF;
END; $$;


