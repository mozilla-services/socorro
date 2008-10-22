<?php
/**
 * This controller displays system status.
 */
class Status_Controller extends Controller {

    /**
     * Default status dashboard nagios can hit up for data.
     */
    public function index() {
      $server_status_model = new Server_Status_Model();
      $serverStats = $server_status_model->loadStats();
        cachecontrol::set(array(
  	  'expires' => time() + (60 * 5) // 5 minutes
        ));

        $this->setViewData(array(
	    'server_stats'            => $serverStats->data,
            'plotData'                => $serverStats->getPlotData(),
            'status'                  => $serverStats->status()
        ));

    }

}
