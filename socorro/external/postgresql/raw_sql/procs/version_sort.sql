CREATE OR REPLACE FUNCTION version_sort(version text, beta_no integer DEFAULT 0, channel citext DEFAULT ''::citext) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $_$
DECLARE vne TEXT[];
    sortstring TEXT;
    dex INT;
BEGIN

    -- TODO make this thing deal with non-numeric beta identifiers HAH
    -- regexp the version number into tokens
    vne := regexp_matches( version, $x$^(\d+)\.(\d+)([a-zA-Z]*)(\d*)(?:\.(\d+))?(?:([a-zA-Z]+)(\d*))?.*$$x$ );
    
    -- bump betas after the 3rd digit back
    vne[3] := coalesce(nullif(vne[3],''),vne[6]);
    vne[4] := coalesce(nullif(vne[4],''),vne[7]);

    -- handle betal numbers
    IF beta_no > 0 THEN
        vne[3] := 'b';
        vne[4] := beta_no::TEXT;
    END IF;
    
    --handle final betas
    IF version LIKE '%(beta)%' THEN
        vne[3] := 'b';
        vne[4] := '99';
    END IF;
    
    --handle release channels
    CASE channel
        WHEN 'nightly' THEN
            vne[3] := 'a';
            vne[4] := '1';
        WHEN 'aurora' THEN
            vne[3] := 'a';
            vne[4] := '2';
        WHEN 'beta' THEN
            vne[3] := 'b';
            vne[4] := COALESCE(nullif(vne[4],''),99);
        WHEN 'release' THEN
            vne[3] := 'r';
            vne[4] := '0';
        WHEN 'ESR' THEN
            vne[3] := 'x';
            vne[4] := '0';
        ELSE
            NULL;
    END CASE;
    
    -- fix character otherwise
    IF vne[3] = 'esr' THEN
        vne[3] := 'x';
    ELSE
        vne[3] := COALESCE(nullif(vne[3],''),'r');
    END IF;
    
    --assemble string
    sortstring := version_sort_digit(vne[1]) 
        || version_sort_digit(vne[2]) 
        || version_sort_digit(vne[5]) 
        || vne[3]
        || version_sort_digit(vne[4]) ;
        
    RETURN sortstring;
END;$_$;


