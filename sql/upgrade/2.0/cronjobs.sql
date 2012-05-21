/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

create table cronjobs (
   cronjob  text not null primary key,
   enabled boolean not null default true,
   frequency interval,
   lag interval,
   last_success timestamptz,
   last_target_time timestamptz,
   last_failure timestamptz,
   failure_message text,
   description text
);

alter table cronjobs owner to breakpad_rw;
