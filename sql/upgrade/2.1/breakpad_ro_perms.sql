/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

\set ON_ERROR_STOP

-- make sure by default new tables are readable by the breakpad group role

alter default privileges in schema public
grant select on tables to breakpad;

--blanket grant in order to catch up old tables

grant select on all tables in schema public to breakpad;

