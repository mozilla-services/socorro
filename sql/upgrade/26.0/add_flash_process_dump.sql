-- This Source Code Form is subject to the terms of the Mozilla Public
-- License, v. 2.0. If a copy of the MPL was not distributed with this
-- file, You can obtain one at http://mozilla.org/MPL/2.0/.

\set ON_ERROR_STOP on

DO $f$
BEGIN

PERFORM 1 FROM information_schema.columns
        WHERE table_name = 'reports'
        AND column_name = 'flash_process_dump';


IF NOT FOUND THEN
    ALTER TABLE reports ADD COLUMN flash_process_dump text;
END IF;

PERFORM 1 FROM information_schema.columns
        WHERE table_name = 'reports_clean'
        AND column_name = 'flash_process_dump';

IF NOT FOUND THEN
    CREATE TYPE flash_process_dump_type AS ENUM ('Sandbox', 'Broker');
    ALTER TABLE reports_clean ADD COLUMN flash_process_dump flash_process_dump_type;
END IF;

END;
$f$;

COMMIT;
