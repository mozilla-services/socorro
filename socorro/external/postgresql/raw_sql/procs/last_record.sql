CREATE OR REPLACE FUNCTION last_record(tablename text) RETURNS integer
    LANGUAGE plpgsql
    AS $$
declare curdate timestamp;
  resdate timestamp;
  ressecs integer;
begin

CASE WHEN tablename = 'reports' THEN
  curdate:= now() - INTERVAL '3 days';
  EXECUTE 'SELECT max(date_processed)
  FROM reports
  WHERE date_processed > ' || 
        quote_literal(to_char(curdate, 'YYYY-MM-DD')) 
        || ' and date_processed < ' ||
        quote_literal(to_char(curdate + INTERVAL '4 days','YYYY-MM-DD'))
    INTO resdate;
  IF resdate IS NULL THEN
     resdate := curdate;
  END IF;
WHEN tablename = 'top_crashes_by_signature' THEN
  SELECT max(window_end)
  INTO resdate
  FROM top_crashes_by_signature;
WHEN tablename = 'top_crashes_by_url' THEN
  SELECT max(window_end)
  INTO resdate
  FROM top_crashes_by_url;
ELSE
  resdate:= null;
END CASE;

ressecs := round(EXTRACT('epoch' FROM ( now() - resdate )))::INT;

RETURN ressecs;

END;$$;


