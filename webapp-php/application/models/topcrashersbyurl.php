<?php
/**
 * Manage data in the `topcrashers` table.
 *
 * @todo	These methods should take a start and an end date as parameters.
 * @todo   	They should not return an array with dates.
 */
class TopcrashersByUrl_Model extends Model {

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

	/**
   	 * Returns a list of existing reports based on the product visibility table.
	 *
	 * @access 	public
	 * @param	string	The date YYYY-MM-DD
	 * @return 	array 	An array of reports
   	 */
	public function listReports($aDate = NULL)
	{
	  if(! $aDate) {
	    $aDate = date("Y-m-d",time());
	  }
	  $sql = "SELECT p.product, p.version, (NOT ignore and start_date <= ? and ? <= end_date) as enabled
	 			FROM product_visibility pv
	            JOIN productdims p ON pv.productdims_id = p.id
	           	ORDER BY p.id DESC";
	  return $this->db->query($sql,$aDate,$aDate);
	}
	
	/* */
}
