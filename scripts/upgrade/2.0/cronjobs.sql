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
