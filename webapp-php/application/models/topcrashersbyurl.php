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
    $sql = "/* soc.web tcbyrul geturls */ " .
           "SELECT SUM(facts.count) AS count, urldims.url FROM topcrashurlfacts AS facts " .
           "JOIN urldims ON urldims.id = facts.urldims_id " .
           "WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= day " . 
           "  AND day <= TIMESTAMP WITHOUT TIME ZONE '$end_date' " .
           "  AND productdims_id = $product_id " .
           "  AND urldims.url != 'ALL' " .
           "  AND signaturedims_id != 1 " .
           "GROUP BY (urldims.url) " .
           "ORDER BY count DESC " .
           "LIMIT 100 OFFSET $offset";
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
    //$aTime = strtotime('2008-11-20');
    $end_date = date("Y-m-d", $aTime);
    $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
    $product_id = $this->getProductId($product, $version);
    $sql = "/* soc.web tcbyrul getdmns */ " .
           "SELECT SUM(facts.count) AS count, urldims.domain FROM topcrashurlfacts AS facts " .
           "JOIN urldims ON urldims.id = facts.urldims_id " .
           "WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= day " . 
           "AND day <= TIMESTAMP WITHOUT TIME ZONE '$end_date' " .
           "AND productdims_id = $product_id " .
           "AND urldims.url = 'ALL' " .
           "AND signaturedims_id = 1 " .
           "GROUP BY (urldims.domain) " .
           "ORDER BY count DESC " .
           "LIMIT 100 OFFSET $offset";
      return array($start_date, $end_date, 
      //list of crash objects, which have a url and count
      $this->fetchRows($sql)
      );
    }
    public function endingOn(){
      return '2008-09-20';
    }

    public function getUrlsByDomain($product, $version, $domain, $page){
      $offset = ($page -1) * 50;
      $aTime = time();
      //$aTime = strtotime('2008-11-20');
      $end_date = date("Y-m-d", $aTime);
      $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
      $product_id = $this->getProductId($product, $version);
      $sqlFromReports =  "/* soc.web tcburl urlsbydomain */ " .
        "SELECT SUM(facts.count) AS count, urldims.url FROM topcrashurlfacts AS facts " .
        "JOIN urldims ON urldims.id = facts.urldims_id " .
        "WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= day " .
        "AND day <= TIMESTAMP WITHOUT TIME ZONE '$end_date' " . 
        "AND productdims_id = $product_id " . 
        "AND urldims.url != 'ALL' " .
        "AND urldims.domain = '$domain' " .
        "AND signaturedims_id = 1 " .
        "GROUP BY (urldims.url) " .
        "ORDER BY count DESC " .
        "LIMIT 50 OFFSET $offset ";

      $signatures = $this->fetchRows($sqlFromReports);

      return $signatures;

    }

    public function getSignaturesByUrl($product, $version, $url, $page){
      $offset = ($page -1) * 50;
      $aTime = time();
      //$aTime = strtotime('2008-11-20');
      $end_date = date("Y-m-d", $aTime);
      $start_date = date("Y-m-d", $aTime - (60 * 60 * 24 * 14) + 1);
      $product_id = $this->getProductId($product, $version);
      $sqlFromReports = "/* soc.web tcburl sigbyurl */ " .
        "SELECT SUM(count) as count, signaturedims.signature " .
        "FROM topcrashurlfacts AS facts  " .
        "JOIN signaturedims ON facts.signaturedims_id = signaturedims.id " .
        "JOIN urldims ON facts.urldims_id = urldims.id " .
        "WHERE TIMESTAMP WITHOUT TIME ZONE '$start_date' <= day " .
        "AND day <= TIMESTAMP WITHOUT TIME ZONE '$end_date' " .
        "AND urldims.url = '$url' " .
        "AND productdims_id = $product_id " . 
        "AND signaturedims.id != 1 " .
        "GROUP BY signature " .
        "ORDER BY count DESC " .
        "LIMIT 50 OFFSET $offset;";

      $signatures = $this->fetchRows($sqlFromReports);
      $comments = $this->getSigCommentsByUrl($product, $version, $url);
      foreach($signatures as $sig){
        if( array_key_exists( $sig->signature, $comments )){
          $sig->comments = $comments[$sig->signature];
	}
      }
      return $signatures;
    }
    public function getSigCommentsByUrl($product, $version, $url){
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
        "AND urldims.url = '$url' ";
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

    /**
     * TODO: We should cache all calls to this method. 
     * There aren't many values and it is reused heavily.
     */
    public function getProductId($product, $version){
      $sql = "/* soc.web tcburl proddim.id */ " .
         "SELECT id FROM productdims " .
         "WHERE version = '$version' " .
         "AND product = '$product' " .
	"AND os_name = 'ALL' ";
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
}
