BEGIN;

--
-- As of 9.1, type citext should be marked collatable.  There is no ALTER TYPE
-- command for this, so we have to do it by poking the pg_type entry directly.
-- We have to poke any derived copies in pg_attribute or pg_index as well,
-- as well as those for arrays/domains based directly or indirectly on citext.
-- Notes: 100 is the OID of the "pg_catalog.default" collation --- it seems
-- easier and more reliable to hard-wire that here than to pull it out of
-- pg_collation.  Also, we don't need to make pg_depend entries since the
-- default collation is pinned.
--
WITH RECURSIVE typeoids(typoid) AS
  ( SELECT 'citext'::pg_catalog.regtype UNION
    SELECT oid FROM pg_catalog.pg_type, typeoids
      WHERE typelem = typoid OR typbasetype = typoid )
UPDATE pg_catalog.pg_type SET typcollation = 100
FROM typeoids
WHERE oid = typeoids.typoid;
WITH RECURSIVE typeoids(typoid) AS
  ( SELECT 'citext'::pg_catalog.regtype UNION
    SELECT oid FROM pg_catalog.pg_type, typeoids
      WHERE typelem = typoid OR typbasetype = typoid )
UPDATE pg_catalog.pg_attribute SET attcollation = 100
FROM typeoids
WHERE atttypid = typeoids.typoid;
UPDATE pg_catalog.pg_index SET indcollation[0] = 100
WHERE indclass[0] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[1] = 100
WHERE indclass[1] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[2] = 100
WHERE indclass[2] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[3] = 100
WHERE indclass[3] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[4] = 100
WHERE indclass[4] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[5] = 100
WHERE indclass[5] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[6] = 100
WHERE indclass[6] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
UPDATE pg_catalog.pg_index SET indcollation[7] = 100
WHERE indclass[7] IN (
  WITH RECURSIVE typeoids(typoid) AS
    ( SELECT 'citext'::pg_catalog.regtype UNION
      SELECT oid FROM pg_catalog.pg_type, typeoids
        WHERE typelem = typoid OR typbasetype = typoid )
  SELECT oid FROM pg_catalog.pg_opclass, typeoids
  WHERE opcintype = typeoids.typoid
);
-- somewhat arbitrarily, we assume no citext indexes have more than 8 columns

COMMIT;

