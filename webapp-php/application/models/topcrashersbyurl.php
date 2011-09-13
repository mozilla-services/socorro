<?php
/**
 * Manage data in the `topcrashers` table.
 *
 * @todo	These methods should take a start and an end date as parameters.
 * @todo   	They should not return an array with dates.
 */
class TopcrashersByUrl_Model extends Model {

	/**
	 * Given a database result containing
	 * urls and/or domains, modifies the results
	 * by applying privacy policies such as
	 * replacing file urls with a hardcoded
	 * file_detected_BLOCKED, etc.
	 *
	 * @param results - Database query results
	 * @return results - Database query results with modifications
	 */
	protected function cleanseUrlsAndDomains(&$results)
	{
	    foreach($results as $result) {
		if (property_exists($result, 'url')) {
		    $result->url = $this->cleanseUrl($result->url);
		}
		if (property_exists($result, 'domain')) {
		    $result->domain = $this->cleanseDomain($result->domain);
		}
	    }
	}

	/**
	 * Given a url, will return the url or
	 * a version of it with privacy policies
	 * applied.
	 *
	 * @param url - an url
	 * @return url or other string
	 */
	protected function cleanseUrl($url)
	{
        if (strpos($url, 'file') === 0) {
            return 'local_file_detected_BLOCKED';
        } else if (preg_match('/^https?:\/\/[^\/]*@[^\/]*\/.*$/', $url)) {
            return 'username_detected_BLOCKED';
        } else if (
            preg_match('/^https?:\/\/.*$/', $url) ||
            preg_match('/^http?:\/\/.*$/', $url)
        ) {
            return $url;
        } else {
            return 'non_http_url_detected_BLOCKED';
        }
	}

	/**
	 * Given a domain, will return the domain or
	 * a version of it with privacy policies
	 * applied.
	 *
	 * @param domain - an domain
	 * @return url or other string
	 */
	protected function cleanseDomain($domain)
	{
	    if (strpos($domain, '@') !== false) {
		    return 'username_detected_BLOCKED';
	    } elseif (!strstr($domain, '.')) {
	        return 'invalid_domain_detected_BLOCKED';
	    } else {
		    return $domain;
	    }
	}


	/**
	 * Find the top crashing urls from the TBD table
	 *
	 * @access 	public
	 * @param	string	The product name
	 * @param 	string	The product version number
	 * @param 	string	The build ID of the product (?)
	 * @param 	string 	The branch number (1.9, 1.9.1, 1.9.2, etc.)
	 * @param 	int 	The page number, used for pagination
	 * @return 	array 	An array of topcrasher objects by domain
	 */
	public function getTopCrashersByUrl($tProduct=NULL, $tVersion=NULL, $build_id=NULL, $branch=NULL, $page=1) {
		$product = $this->db->escape($tProduct);
		$version = $this->db->escape($tVersion);
		$offset = ($page -1) * 100;
		$aTime = time();
		$end_date = date("Y-m-d", $aTime);
		$start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);

    	$sql = "/* soc.web tcbyrul geturls */
            SELECT SUM(tcu.count) as count,	ud.url, at.rank
            FROM top_crashes_by_url tcu
			JOIN urldims ud
			 	ON tcu.urldims_id = ud.id
                AND '$start_date' <= (tcu.window_end - tcu.window_size)
                AND tcu.window_end < '$end_date'
            JOIN productdims pd
 				ON pd.id = tcu.productdims_id
                AND pd.product = $product
                AND pd.version = $version
			LEFT JOIN alexa_topsites at ON ud.domain LIKE '%' || at.domain
            GROUP BY ud.url, at.rank
            ORDER BY count DESC
            LIMIT 100 OFFSET $offset";

	    $results = $this->fetchRows($sql);
	    $this->cleanseUrlsAndDomains($results);
      	return array($start_date, $end_date, $results);
	}

  	/**
   	 * Find top crashing domains from the TBD table
	 *
	 * @access 	public
	 * @param	string	The product name
	 * @param 	string	The product version number
	 * @param 	string	The build ID of the product (?)
	 * @param 	string 	The branch number (1.9, 1.9.1, 1.9.2, etc.)
	 * @param 	int 	The page number, used for pagination
	 * @return 	array 	An array of topcrasher objects by domain
   	 */
  	public function getTopCrashersByDomain($tProduct=NULL, $tVersion=NULL, $build_id=NULL, $branch=NULL, $page=1) {
		$product = $this->db->escape($tProduct);
		$version = $this->db->escape($tVersion);
		$offset = ($page -1) * 100;
		$aTime = time();
		$end_date = date("Y-m-d", $aTime);
		$start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);

		$sql = "/* soc.web tcbyrul getdmns */
		        SELECT sum(tcu.count) as count, ud.domain, at.rank
		        FROM top_crashes_by_url tcu
		 		JOIN urldims ud
					ON tcu.urldims_id = ud.id
					AND '$start_date' <= (tcu.window_end - tcu.window_size)
		            AND tcu.window_end < '$end_date'
				JOIN productdims pd
					ON pd.id = tcu.productdims_id
		            AND pd.product = $product
		            AND pd.version = $version
				LEFT JOIN alexa_topsites at ON ud.domain LIKE '%' || at.domain
		        GROUP BY ud.domain, at.rank
		        ORDER BY count DESC
		        LIMIT 100 OFFSET $offset";

		$results = $this->fetchRows($sql);
		$this->cleanseUrlsAndDomains($results);
      	return array($start_date, $end_date, $results);
  	}

	/**
   	 * Find top crashing domains from the TBD table ordered by their topsite ranking.
	 *
	 * @access 	public
	 * @param	string	The product name
	 * @param 	string	The product version number
	 * @param 	int 	The page number
	 * @return 	array 	An array of topcrasher objects by domain
	 */
  	public function getTopCrashersByTopsiteRank($tProduct=NULL, $tVersion=NULL, $page = 1) {
		$product = $this->db->escape($tProduct);
		$version = $this->db->escape($tVersion);
		$offset = ($page - 1) * 100;
		$aTime = time();
		$end_date = date("Y-m-d", $aTime);
		$start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);

		$sql = "/* soc.web topcrashersbyurl.getTopCrashersByTopsiteRank */
			SELECT
				sum(tcu.count) as count,
				at.domain, at.rank
	        FROM top_crashes_by_url tcu
	 		JOIN urldims ud
				ON tcu.urldims_id = ud.id
				AND '$start_date' <= (tcu.window_end - tcu.window_size)
	            AND tcu.window_end < '$end_date'
			JOIN productdims pd
				ON pd.id = tcu.productdims_id
	            AND pd.product = $product
	            AND pd.version = $version
			JOIN alexa_topsites at ON ud.domain LIKE '%' || at.domain
	        GROUP BY at.domain, at.rank
	        ORDER BY count DESC
	        LIMIT 100 OFFSET $offset";

		$results = $this->fetchRows($sql);
		$this->cleanseUrlsAndDomains($results);
	  	return array($start_date, $end_date, $results);
	}

  	/**
   	 * Fetch all of the crashing URLs associated with a particular domain.
	 *
	 * @access 	public
	 * @param	string	The product name
	 * @param 	string	The product version number
	 * @param 	string 	The domain name
	 * @param 	int 	The page number, used for pagination
	 * @return 	array 	An array of signatures
   	 */
	public function getUrlsByDomain($tProduct, $tVersion, $tDomain, $page=0){
 		$product = $this->db->escape($tProduct);
 		$version = $this->db->escape($tVersion);
 		$domain = $this->db->escape($tDomain);
 		$offset = ($page -1) * 50;
 		$aTime = time();
 		$end_date = date("Y-m-d", $aTime);
 		$start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
 		$sql =  "/* soc.web tcburl urlsbydomain */
 		        SELECT sum(tcu.count) as count, ud.url
				FROM top_crashes_by_url tcu
				JOIN urldims ud
					ON tcu.urldims_id = ud.id
					AND ud.domain = $domain
 		        	AND '$start_date' <= (tcu.window_end - tcu.window_size)
 		        	AND tcu.window_end < '$end_date'
 		        JOIN productdims pd
					ON tcu.productdims_id = pd.id
 		            AND pd.product = $product
 		            AND pd.version = $version
				GROUP BY ud.url
				ORDER BY count DESC
				LIMIT 50 OFFSET $offset";

 		return $this->fetchRows($sql);
	}

  	/**
   	 * Fetch all of the crash signatures associated with a particular URL.
	 *
	 * @access 	public
	 * @param	string	The product name
	 * @param 	string	The product version number
	 * @param 	string 	The URL
	 * @param 	int 	The page number, used for pagination
	 * @return 	array 	An array of signatures
   	 */
	public function getSignaturesByUrl($tProduct, $tVersion, $tUrl, $page){
		$product = $this->db->escape($tProduct);
		$version = $this->db->escape($tVersion);
		$url = $this->db->escape($tUrl);
		$offset = ($page -1) * 50;
		$aTime = time();

		$end_date = date("Y-m-d", $aTime);
		$start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);

		$sql = "/* soc.web tcburl sigbyurl */
		  		SELECT sum(tucs.count) as count, tucs.signature
		  		FROM top_crashes_by_url tcu
		  		JOIN urldims ud
					ON tcu.urldims_id = ud.id
		  			AND '$start_date' <= (tcu.window_end - tcu.window_size)
					AND tcu.window_end < '$end_date'
					AND ud.url = $url
		  		JOIN productdims pd
					ON pd.id = tcu.productdims_id
		  			AND pd.product = $product
					AND pd.version = $version
				JOIN top_crashes_by_url_signature tucs ON tucs.top_crashes_by_url_id = tcu.id
		  		GROUP BY tucs.signature
		  		ORDER BY 1 DESC
		  		LIMIT 50";

		return $this->fetchRows($sql);
	}

	/* */
}
