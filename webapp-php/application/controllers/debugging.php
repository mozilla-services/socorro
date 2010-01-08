<?php
/**
 * This controller is for debugging stage or production ONLY
 * ***NOTE*** should be empty most of the time. Don't leave any 
 * wacky code in the tree, which could become an exploit.
 */
class Debugging_Controller extends Controller {

    /**
     * Default status dashboard nagios can hit up for data.
     */
    public function index() {
	$this->auto_render = false;
	echo "3rd try\n";
	$m = new Common_Model;
	$rs = $m->fetchRows("SELECT id FROM productdims WHERE product = 'Firefox' AND version = '3.5.6';");
/*"select
          CAST(ceil(EXTRACT(EPOCH FROM (window_end - timestamp without time zone '2009-12-25 00:00:00' - interval '8 hours')) / 86400) AS INT) * interval '24 hours' + timestamp without time zone '2009-12-25 00:00:00' as day,
          case when os.os_name = 'Windows NT' then
            'Windows'
          when os.os_name = 'Mac OS X' then
            'Mac'
          else
            os.os_name
          end as os_name,
          sum(count)
      from
          top_crashes_by_signature tcbs
              outer join osdims os on tcbs.osdims_id = os.id
                  and os.os_name in ('Windows','Mac OS X','Linux','Windows NT')
      where
          (timestamp without time zone '2009-12-25 00:00:00' - interval '8 hours') < window_end
          and window_end <= (timestamp without time zone '2010-01-08 00:00:00' - interval '8 hours')
          and productdims_id = 169
      group by
          day,
          os_name
      order by
          1, 2;");
*/
	echo var_dump($rs);
    }
}
