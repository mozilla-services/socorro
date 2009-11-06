<?php
/**
 * Manage data in the topcrashers table.
 */
class Topcrashers_Model extends Model {

    /**
     * Finds the time when the table was last updated for the given criteria
     * @param string A branch Example: 1.9.3
     * @return unix time or FALSE for no entries
     */
    public function lastUpdatedByBranch($branch)
    {
        $sql = "/* soc.web topcrash.lastupdatebybranch */ 
            SELECT window_end AS last_updated
            FROM top_crashes_by_signature tcs 
            JOIN productdims p ON tcs.productdims_id = p.id AND 
                             p.branch = ?
            ORDER BY window_end DESC LIMIT 1";
	return $this->_lastUpdated($sql, array($branch));
    }

    /**
     * Finds the time when the table was last updated for the given criteria
     * @param string A product
     * @param string A version Example 3.6a1pre
     * @return unix time or FALSE for no entries
     */
    public function lastUpdatedByVersion($product, $version) 
    {
	$sql = "/* soc.web topcrash.lastupdatebyver */ 
            SELECT max(window_end) AS last_updated
            FROM top_crashes_by_signature tcs 
            JOIN productdims p ON tcs.productdims_id = p.id
            WHERE p.product = ? AND 
                  p.version = ?";
	return $this->_lastUpdated($sql, array($product, $version));
    }

    /**
     * Common logic for fetching last updated time from the database
     * @param string sql
     * @param array params
     * @return time or FALSE if there are now entries
     */
    private function _lastUpdated($sql, $params)
    {
	$rows = $this->fetchRows($sql, TRUE, $params);
        if ($rows) {
	    // make a 2 week window
	    return strtotime($rows[0]->last_updated );
	}
	return FALSE;
    }
    /**
     * Retrieves the total number of crashes for given perio
     * @param string The branch id Example: 1.9.1
     * @param int the earliest time to start looking for crashes
     * @param int the latest time to look at for crashes
     * @return int total crashes
     * @see time function for generating $start and $end
     */
    public function getTotalCrashesByBranch($branch, $start, $end)
    {
	$sql = "/* soc.web topcrash.totcrashbranch */ 
            SELECT SUM(tcs.count) as total
            FROM top_crashes_by_signature tcs
            JOIN productdims pd on tcs.productdims_id = pd.id 
            JOIN branches USING (product, version)
            WHERE branches.branch = ? AND 
                  window_end >= ? AND 
                  window_end < ? ";
	return $this->_getTotalCrashes($sql, array($branch, $this->t($start), $this->t($end)));
    }

    /**
     * Retrieves the total number of crashes for given perio
     * @param string product name 
     * @param string version Example: 3.7a1pre
     * @param int the earliest time to start looking for crashes
     * @param int the latest time to look at for crashes
     * @return int total crashes
     * @see time function for generating $start and $end
     */
    public function getTotalCrashesByVersion($product, $version, $start, $end)
    {
	$sql = "/* soc.web topcrash.totcrashvers */ 
            SELECT SUM(tcs.count) as total
            FROM top_crashes_by_signature tcs
            JOIN productdims pd on tcs.productdims_id = pd.id AND 
                 pd.product = ? AND 
                 pd.version = ? 
            WHERE window_end >= ? AND
                  window_end < ? ";
	return $this->_getTotalCrashes($sql, array($product, $version, $this->t($start), $this->t($end)));
    }
    /**
     * Common way to process total crashes db results
     * @param string SQL to run
     * @param array Parameters bound by SQL
     * @return int Total number of crashes
     */
    private function _getTotalCrashes($sql, $params)
    {
	$tot_rows = $this->fetchRows($sql, TRUE, $params);
	if ($tot_rows) {
	    return $total_crashes = $tot_rows[0]->total;
	}
	return 0;
    }

    /**
     * Utility method for subtracting days
     * @param int Number of Days
     * @param int Date in unix time format
     * @param int New Date in unix time format
     * @see time for generating $end
     */
    public function timeBeforeOffset($days, $end)
    {
	return $end - (60 * 60 * 24 * $days);
    }
    /**
     * Utility method for formatting Postgres friendly dates
     * @param int Date in unix time format
     * @return string The formatted date
     */
    private function t($time)
    {
	return date("Y-m-d H:i:s", $time);
    }

    /**************************************************************************************************************
    topCrashersBySignature object - Dynamic Class generated from DB results in 
                                    getTopCrashersByVersion and getTopCrashersByBranch
    layout - object properties and example values:
    {
	"product":"Thunderbird",
	"version":"3.0b3",
	"signature":"nsCharTraits<char>::compareLowerCaseToASCIINullTerminated(char const*, unsigned int, char const*)",
	"percent":"0.0751807228915663",
	"total":"156",
	"win":"156","mac":"0","linux":"0"}
	
    }
    **************************************************************************************************************/

    /**
     * Find top crashes from the aggregate topcrashers table.
     * @param string product name 
     * @param string version Example: 3.7a1pre
     * @param int LIMIT for size of search results
     * @param int the earliest time to start looking for crashes
     * @param int the latest time to look at for crashes
     * @param in the total number of crashes for this period
     * @return array of topCrashersBySignature object (see comment above)
     */
    public function getTopCrashersByVersion($product=NULL, $version=NULL, $limit=100, $start=NULL, $end=NULL, $total_crashes=1) {
        $sql = "/* soc.web topcrash.byversion */ 
            SELECT p.product AS product,
                   p.version AS version,
                   tcs.signature,
                   cast(sum(tcs.count) as float) / ? as percent,
                   sum(tcs.count) as total,
                   sum(case when o.os_name LIKE 'Windows%' then tcs.count else 0 end) as win,
                   sum(case when o.os_name = 'Mac OS X' then tcs.count else 0 end) as mac,
                   sum(case when o.os_name = 'Linux' then tcs.count else 0 end) as linux 
            FROM top_crashes_by_signature tcs
            JOIN productdims p ON tcs.productdims_id = p.id
            JOIN osdims o ON tcs.osdims_id = o.id 
            WHERE p.product = ? AND 
                  p.version = ? AND 
                  window_end >= ? AND 
                  window_end < ?
            GROUP BY p.product, p.version, tcs.signature
            HAVING sum(tcs.count) > 0
            ORDER BY total desc
            LIMIT ?";
        return $this->fetchRows($sql, TRUE,
				array($total_crashes, $product, $version, $this->t($start), $this->t($end), $limit));
    }

    /**
     * Find top crashes from the aggregate topcrashers table.
     * @param string The branch id Example: 1.9.1
     * @param int LIMIT for size of search results
     * @param int the earliest time to start looking for crashes
     * @param int the latest time to look at for crashes
     * @param in the total number of crashes for this period
     * @return array of topCrashersBySignature object (see comment above)
     */
    public function getTopCrashersByBranch($branch, $limit=100, $start=NULL, $end=NULL, $total_crashes=1) {
        $sql = "/* soc.web topcrash.bybranch */ 
            SELECT p.branch,
                   tcs.signature,
                   cast(sum(tcs.count) as float) / ? as percent,
                   sum(tcs.count) as total,
                   sum(case when o.os_name LIKE 'Windows%' then tcs.count else 0 end) as win,
                   sum(case when o.os_name = 'Mac OS X' then tcs.count else 0 end) as mac,
                   sum(case when o.os_name = 'Linux' then tcs.count else 0 end) as linux 
            FROM top_crashes_by_signature tcs
            JOIN productdims p ON tcs.productdims_id = p.id AND 
                 p.branch = ?
            JOIN osdims o ON tcs.osdims_id = o.id 
            WHERE window_end >= ? AND 
                  window_end < ?
            GROUP BY p.branch, tcs.signature
            HAVING sum(tcs.count) > 0
            ORDER BY total desc
            LIMIT ?";
        return $this->fetchRows($sql, TRUE,
				array($total_crashes, $branch, $this->t($start), $this->t($end), $limit));
    }

}
