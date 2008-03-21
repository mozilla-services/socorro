
drop table jobs;
drop table processors;

create table processors (
  id serial primary key,
  name varchar(255) not null,
  startDateTime timestamp not null,
  lastSeenDateTime timestamp
);
create index idx_processor_name on processors(name);

create table jobs (
  id serial primary key,
  pathname varchar(1024) not null,
  uuid varchar(50) not null unique,
  owner integer references processors (id) on delete cascade,
  priority integer default 0,
  queuedDateTime timestamp,
  startedDateTime timestamp,
  completedDateTime timestamp,
  success boolean,
  message text
);

