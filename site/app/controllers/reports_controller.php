<?php
class ReportsController extends AppController {
    var $name = 'Reports';
    
    function view(){
        if($this->params["url"]["uuid"]){
            $uuid = $this->params["url"]["uuid"];
        }
        
        $report = $this->Report->findByUuid($uuid);
        $this->set('report', $report["Report"]);
    }
}
?>