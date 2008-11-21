<?php defined('SYSPATH') or die('No direct script access.');

/**
 * Model for server_status db table.
 */
class Server_Status_Model extends Model {
  
  public function loadStats(){
    return new Server_Stats( $this->fetchRows("/* soc.web servstat.loadStat */ SELECT * FROM server_status ORDER BY date_created DESC LIMIT 12") );
  }

}

/**
 * Represents a snapshot across time of the Socorro servers health.
 */
class Server_Stats {
  const HAPPY   = 'happy';
  const GRUMPY  = 'grumpy';
  const DEATHLY = 'deathly';

  public $data;

  /**
   * data - An array where each element is an associative arrays 
   * which has server statistics including:
   * avg_process_sec, avg_wait_sec, waiting_job_count, etc
   */
  public function __construct($data){
    $this->data = $data;
  }

  public function getPlotData(){
    $plotData = array();
    foreach( array('avg_process_sec', 'avg_wait_sec', 'waiting_job_count', 'processors_count', 
                       'xaxis_ticks') as $field){
      $plotData[$field] = array();
    }
    $k = count($this->data) - 1;
    for($i = 0; $i < count($this->data); $i += 1){      
      $stat = $this->data[$i];
      $plotData['avg_process_sec'][] = array($k, $stat->avg_process_sec);
      $plotData['avg_wait_sec'][] = array($k, $stat->avg_wait_sec);
      $plotData['waiting_job_count'][] = array($k, $stat->waiting_job_count);
      $plotData['processors_count'][] = array($k, $stat->processors_count);
      $plotData['xaxis_ticks'][] = array($k, date('G:i', strtotime($stat->date_created)));
      $k -= 1;
    }
    return $plotData;
  }
  public function status(){
    $stat = $this->data[0];
    $stat->avg_wait_sec = 250;
    if( $stat->avg_wait_sec < 300 ){
      return Server_Stats::HAPPY;
    }elseif( $stat->avg_wait_sec < 600 ){
      return Server_Stats::GRUMPY;
    }else{
      return Server_Stats::DEATHLY;
    }
  }
}
?>