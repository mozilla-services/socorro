<?php defined('SYSPATH') or die('No direct script access.');

/**
 * Model for server_status db table.
 */
class Server_Status_Model extends Model {
  
  public function loadStats(){
    return new Server_Stats( $this->fetchRows("SELECT * FROM server_status LIMIT 12") );
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

    for($i = 0; $i < count($this->data); $i += 1){
      $stat = $this->data[$i];
      $plotData['avg_process_sec'][] = array($i, $stat->avg_process_sec);
      $plotData['avg_wait_sec'][] = array($i, $stat->avg_wait_sec);
      $plotData['waiting_job_count'][] = array($i, $stat->waiting_job_count);
      $plotData['processors_count'][] = array($i, $stat->processors_count);
      $plotData['xaxis_ticks'][] = array($i, date('G:i', strtotime($stat->date_created)));
    }
    return $plotData;
  }
  public function status(){
    Kohana::log('info', "Calculating status " . Kohana::debug($this->data));
    $stat = end($this->data);
    if( $stat->avg_wait_sec < 60 ){
      return Server_Stats::HAPPY;
    }elseif( $stat->avg_wait_sec < 120 ){
      return Server_Stats::GRUMPY;
    }else{
      return Server_Stats::DEATHLY;
    }
  }
}
?>