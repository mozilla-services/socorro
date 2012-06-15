<?php defined('SYSPATH') or die('No direct script access.');

/**
 * Model for server_status db table.
 */
class Server_Status_Model extends Model {
    
    /**
     * This function converts the current date that is returned from the DB to 
     * an acceptable ISO8601 (using UTC) date that is required by the timeago 
     * plugin used on the server status page.
     * 
     * If the parameter passed is an empty string the function will simply return 
     * a empty string.
     * 
     * @param string The timestamp to be converted
     * @return the converted date or an empty string
     */
    public function toISO8601($conversionDate) {
        return ($conversionDate != "" ? gmdate("M d Y H:i:s", strtotime($conversionDate)) : "");
    }

  public function getStats() {
    $data = $this->fetchRows("/* soc.web servstat.loadStat */ SELECT * FROM server_status ORDER BY date_created DESC LIMIT 12");
    $plotData = array();
    foreach( array('avg_process_sec', 'avg_wait_sec', 'waiting_job_count', 'processors_count',
                       'xaxis_ticks') as $field){
      $plotData[$field] = array();
    }
                       
    $k = count($data) - 1;
    for($i = 0; $i < count($data); $i += 1){
      $stat = $data[$i];
      $plotData['avg_process_sec'][] = array($k, $stat->avg_process_sec);
      $plotData['avg_wait_sec'][] = array($k, $stat->avg_wait_sec);
      $plotData['waiting_job_count'][] = array($k, $stat->waiting_job_count);
      $plotData['processors_count'][] = array($k, $stat->processors_count);
      $plotData['xaxis_ticks'][] = array($k, date('G:i', strtotime($stat->date_created)));
      
        $stat->date_created = $this->toISO8601($stat->date_created);
        $stat->date_recently_completed = $this->toISO8601($stat->date_recently_completed);
        $stat->date_oldest_job_queued = $this->toISO8601($stat->date_oldest_job_queued);
      
      $k -= 1;
    }
    return array( 'data' => $data, 'plotData' => $plotData );
  }

}
?>
