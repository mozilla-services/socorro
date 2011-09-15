Socorro Integration tests

Nothing much to say here: The old code was made obsolete by the materialized
views code checked in 2009, August.

Small amount of testing can be done, as follows:

From the unittest/cron directory, run fillDB -a [your choice of fill options] # note use -a
 Note: fillDB --help gives a list of options. I usually use values like
   -P55 -R4 -S111 but feel free.

From the command line, do the  "get database results" step:

echo "$sql" | psql -F"	" -A -f - -o $output.csv -Utest  test
  # note that's -F<tab> though it almost doesn't matter

for these sql values and appropriate output names such as mtbf_internal.csv:
  "SELECT productdims_id as pid, osdims_id as oid,sum_uptime_seconds as su,report_count as rc, window_end from time_before_failure order by pid,oid,window_end;"
  "SELECT window_end as window_end_woohoo,productdims_id as pid, osdims_id as oid, count as c, uptime as upt, signature from top_crashes_by_signature order by pid,oid,signature,window_end;"
  "SELECT window_end as window_end_woohoo,productdims_id as pid, osdims_id as oid, count as c, urldims_id as u_id from top_crashes_by_url order by pid,oid,u_id,window_end;"

Back to unittest/cron and invoke fillDB [ SAME choice of fill options] # note: No -a
Go to socorro/scripts/config
for each of four config.dist files: commonconfig.py.dist, mtbfconfig.py.dist, topCrashesBy*Config.py.dist
  cp the .dist file to the same name without the .dist (e.g: cp commonconfig.py.dist commonconfig.py)
(Note that ln -s doesn't work)
Go to socorro/scripts
invoke in turn:

startXxx.py --databaseHost=localhost --databaseName=test --databaseUserName=test --databasePassword=t3st --startDate=2007-12-31 --endDate=$DATE
for Xxx in TopCrashesByUrl.py, TopCrashesBySignature.py, Mtbf.py
$DATE is 2008-03-05 for signature and mtbf, but 2008-03-01 for url

Now, do the "get database results" step again, this time using a different csv name in each case, such as mtbf_external.csv

Compare the interal versus the external results.

You can do similar things for two other tables
  'top_crashes_by_url_signature': "SELECT * from top_crashes_by_url_signature order by signature;",
  'topcrashurlfactsreports':      "SELECT * from topcrashurlfactsreports order by uuid;",
But beware that there WILL be diffs because there were bulk insert statments that created ids in different orders.
You may be able to help by selecting only some columns, but you will then lose correlation data.




