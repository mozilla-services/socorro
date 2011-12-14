<?php defined('SYSPATH') or die('No direct script access.');

/**
 * Model for server_status db table.
 */
class Server_Status_Model extends Model {

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
      $k -= 1;
    }
    return array( 'data' => $data, 'plotData' => $plotData );
  }

}
?>
