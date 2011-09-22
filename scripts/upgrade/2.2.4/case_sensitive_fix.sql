BEGIN;

CREATE FUNCTION citext_eq( citext, varchar ) RETURNS bool AS 'citext' LANGUAGE C IMMUTABLE STRICT;

CREATE FUNCTION citext_eq( varchar, citext ) RETURNS bool AS 'citext' LANGUAGE C IMMUTABLE STRICT;

DROP OPERATOR IF EXISTS = ( varchar, citext);

CREATE OPERATOR = (
    LEFTARG    = VARCHAR,
    RIGHTARG   = CITEXT,
    COMMUTATOR = =,
    NEGATOR    = <>,
    PROCEDURE  = citext_eq,
    RESTRICT   = eqsel,
    JOIN       = eqjoinsel,
    HASHES,
    MERGES
);

DROP OPERATOR IF EXISTS = ( citext, varchar);

CREATE OPERATOR = (
    LEFTARG    = CITEXT,
    RIGHTARG   = VARCHAR,
    COMMUTATOR = =,
    NEGATOR    = <>,
    PROCEDURE  = citext_eq,
    RESTRICT   = eqsel,
    JOIN       = eqjoinsel,
    HASHES,
    MERGES
);

CREATE FUNCTION citext_eq( text, citext ) RETURNS bool AS 'citext' LANGUAGE C IMMUTABLE STRICT;

CREATE FUNCTION citext_eq( citext, text ) RETURNS bool AS 'citext' LANGUAGE C IMMUTABLE STRICT;

DROP OPERATOR IF EXISTS = ( text, citext );

CREATE OPERATOR = (
    LEFTARG    = TEXT,
    RIGHTARG   = CITEXT,
    COMMUTATOR = =,
    NEGATOR    = <>,
    PROCEDURE  = citext_text_eq,
    RESTRICT   = eqsel,
    JOIN       = eqjoinsel,
    HASHES,
    MERGES
);

DROP OPERATOR IF EXISTS = ( citext, text);

CREATE OPERATOR = (
    LEFTARG    = CITEXT,
    RIGHTARG   = TEXT,
    COMMUTATOR = =,
    NEGATOR    = <>,
    PROCEDURE  = citext_text_eq,
    RESTRICT   = eqsel,
    JOIN       = eqjoinsel,
    HASHES,
    MERGES
);

COMMIT;