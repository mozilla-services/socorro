<?php
/**
 * Manage data in the topcrashers table.
 *
 * TODO: these methdos should take a start and an end date as parameters.
 *       they should not return an array with dates.
 */
class TopcrashersByUrl_Model extends Model {

  /**
   * Find top crashing urls from the TBD table
   */
  public function getTopCrashersByUrl($product=NULL, $version=NULL, $build_id=NULL, $branch=NULL, $page=1) {
    $offset = ($page -1) * 100;
    $aTime = time();
    //$aTime = strtotime('2008-11-20');
    $end_date = date("Y-m-d", $aTime);
    $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);

    $product_id = $this->getProductId($product, $version);
    $sql = "/* soc.web tcbyrul geturls */ 
           SELECT SUM(facts.count) AS count, urldims.url 
           FROM top_crashes_by_url AS facts
           JOIN urldims ON urldims.id = facts.urldims_id 
           WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= facts.window_end
             AND facts.window_end <= TIMESTAMP WITHOUT TIME ZONE '$end_date' 
             AND productdims_id = $product_id 
           GROUP BY (urldims.url) 
           ORDER BY count DESC 
           LIMIT 100 OFFSET $offset";

    return array($start_date, $end_date, 
      //list of crash objects, which have a url and count
      $this->fetchRows($sql)
      );
    }
  /**
   * Find top crashing domains from the TBD table
   */
  public function getTopCrashersByDomain($product=NULL, $version=NULL, $build_id=NULL, $branch=NULL, $page=1) {
    $offset = ($page -1) * 100;
    $aTime = time();
    $end_date = date("Y-m-d", $aTime);
    $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
    $product_id = $this->getProductId($product, $version);
    $sql = "/* soc.web tcbyrul getdmns */
           SELECT SUM(facts.count) AS count, urldims.domain
           FROM top_crashes_by_url AS facts
           JOIN urldims ON urldims.id = facts.urldims_id 
           WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= facts.window_end
             AND facts.window_end <= TIMESTAMP WITHOUT TIME ZONE '$end_date' 
             AND productdims_id = $product_id 
           GROUP BY (urldims.domain) 
           ORDER BY count DESC 
           LIMIT 100 OFFSET $offset";
      return array($start_date, $end_date, 
      //list of crash objects, which have a url and count
      $this->fetchRows($sql)
      );
    }

    public function getUrlsByDomain($product, $version, $tDomain, $page=0){
      $domain = $this->db->escape($tDomain);
      $offset = ($page -1) * 50;
      $aTime = time();
      $end_date = date("Y-m-d", $aTime);
      $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
      $product_id = $this->getProductId($product, $version);
      $sqlFromReports =  "/* soc.web tcburl urlsbydomain */
SELECT SUM(top_crashes_by_url.count) AS count, urldims.url FROM top_crashes_by_url
JOIN urldims ON urldims.id = top_crashes_by_url.urldims_id 
WHERE top_crashes_by_url.window_end <= '$end_date' AND 
      top_crashes_by_url.window_end > '$start_date'
      AND productdims_id = 1 AND urldims.domain = $domain
GROUP BY (urldims.url) 
ORDER BY count DESC LIMIT 50 OFFSET $offset";
      $signatures = $this->fetchRows($sqlFromReports);

      return $signatures;

    }

    public function getSignaturesByUrl($product, $version, $tUrl, $page){
      $url = $this->db->escape($tUrl);
      $offset = ($page -1) * 50;
      $aTime = time();
      
      $end_date = date("Y-m-d", $aTime);
      $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);

      $product_id = $this->getProductId($product, $version);
      $sqlFromReports = "/* soc.web tcburl sigbyurl */
                         SELECT tcu.count, tcus.signature 
                           FROM top_crashes_by_url tcu
                           JOIN urldims u ON tcu.urldims_id = u.id
                           JOIN top_crashes_by_url_signature tcus ON tcu.id = tcus.top_crashes_by_url_id
                         WHERE u.url = $url
                           AND '$start_date' <= (tcu.window_end - tcu.window_size)
                           AND tcu.window_end < '$end_date'";

      $signatures = $this->fetchRows($sqlFromReports);
      $comments = $this->getSigCommentsByUrl($product, $version, $url);
      foreach($signatures as $sig){
        if( array_key_exists( $sig->signature, $comments )){
          $sig->comments = $comments[$sig->signature];
	}
      }
      return $signatures;
    }

    public function getSigCommentsByUrl($product, $version, $tUrl){
      $url = $this->db->escape($tUrl);
      $aTime = time();
      //$aTime = strtotime('2008-11-20');
      $end_date = date("Y-m-d", $aTime);
      $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
      $sql = "/* soc.web tbcurl comm4sig */ " . 
        "SELECT signaturedims.signature, crashes.comments, crashes,uuid " .
        "FROM topcrashurlfacts AS facts " .
        "JOIN topcrashurlfactsreports AS crashes ON facts.id = crashes.topcrashurlfacts_id " .
        "JOIN urldims ON facts.urldims_id = urldims.id " .
        "JOIN signaturedims ON facts.signaturedims_id = signaturedims.id " .
        "WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= facts.day " .
        "AND facts.day <= TIMESTAMP WITHOUT TIME ZONE '$end_date' " .
        "AND urldims.url = $url ";
      $rows = $this->fetchRows($sql);
      $sigToCommentMap = array();
      foreach( $rows as $row ){
        if( ! array_key_exists( $row->signature, $sigToCommentMap )){
          $sigToCommentMap[$row->signature] = array();
	}
        array_push($sigToCommentMap[$row->signature], 
                                       array('comments' => $row->comments,
                                            'report-id' => $row->uuid));
      }
      return $sigToCommentMap;
    }

    public function getProductId($tProduct, $tVersion){
      $product = $this->db->escape($tProduct);
      $version = $this->db->escape($tVersion);

      $sql = "/* soc.web tcburl proddim.id */
              SELECT id FROM productdims
              WHERE version = $version
              AND product = $product";
      $rows = $this->fetchRows($sql);
      if(count($rows) != 1){
	Kohana::log('error', "Unable to getProductId for $product $version got " . Kohana::debug($rows));
      }
      if( count( $rows ) > 0 ){
        return $rows[0]->id;
      }else{
	Kohana::log('error', "Unknown product $product $version");
        return -1;
      }
    }
    /**
     * Returns a list of existing reports based on the 
     * top crashers by url config table 'tcbyurlconfig'
     */
    public function listReports()
    {
        $sql = "SELECT p.product, p.version, conf.enabled FROM tcbyurlconfig conf
                   JOIN productdims p ON conf.productdims_id = p.id
                   ORDER BY p.id DESC";
        return $this->fetchRows($sql);
    }
}
