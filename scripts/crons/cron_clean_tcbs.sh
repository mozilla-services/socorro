#!/bin/bash
# Periodically clean top_crash_by_signature table

. /etc/socorro/socorrorc

NAME=`basename $0 .sh`

if [[ ! "$databaseHost" && "$databaseUserName" && "$databaseName" ]]
then
  echo "error: need databaseHost, databaseUserName, databaseName set in $SOCORRO_CONFIG"
fi

lock $NAME

pyjob $NAME createPartitions
EXIT_CODE=$?
if [ $EXIT_CODE != 0 ]
then
  echo "createPartitions failed, exiting $NAME early!"
  unlock $NAME
  exit $EXIT_CODE
fi

psql -t -h ${databaseHost} -U ${databaseUserName} ${databaseName} <<SQL_END
delete from top_crashes_by_signature
where id in
    (select
         tcbs.id
     from
         top_crashes_by_signature tcbs
            join product_visibility pv on tcbs.productdims_id = pv.productdims_id
     where
         tcbs.window_end < (case when now() < pv.end_date then now()
                                 else pv.end_date end) - interval '56 days');
SQL_END
EXIT_CODE=$?

unlock $NAME

exit $EXIT_CODE
