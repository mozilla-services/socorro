CREATE OR REPLACE FUNCTION crontabber_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
	
	NEW.last_updated = now();
	RETURN NEW;
	
END; $$;


