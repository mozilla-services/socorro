\set ON_ERROR_STOP 1

-- create new table for emails

SELECT create_table_if_not_exists('emails',
$t$
CREATE TABLE emails (
    email citext not null,
    last_sending timestamp with time zone,
    constraint emails_key primary key ( email )
);$t$, 'breakpad_rw' );
