CREATE OR REPLACE FUNCTION crontabber_nodelete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN

	RAISE EXCEPTION 'you are not allowed to add or delete records from the crontabber table';

END;
$$;


