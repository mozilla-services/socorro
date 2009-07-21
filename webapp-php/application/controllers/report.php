<?php
require_once(Kohana::find_file('libraries', 'bugzilla', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'MY_SearchReportHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'crash', TRUE, 'php'));
/**
 * List, search, and show crash reports.
 */
class Report_Controller extends Controller {

    /**
     * List reports for the given search query parameters.
     */
    public function do_list() {

        $helper = new SearchReportHelper();

        $branch_data = $this->branch_model->getBranchData();
        $platforms   = $this->platform_model->getAll();

	$d = $helper->defaultParams();
	$d['signature'] = '';
        $params = $this->getRequestParameters($d);

        $helper->normalizeParams( $params );

        cachecontrol::set(array(
            'etag'     => $params,
            'expires'  => time() + ( 60 * 60 )
        ));

        $reports = $this->common_model->queryReports($params);
	if (count($reports) == 0) {
	  header("No data for this query", TRUE, 404);
          $this->setView('common/nodata');
	} else {
          $builds  = $this->common_model->queryFrequency($params);

  	  if (count($builds) > 1){
	    $crashGraphLabel = "Crashes By Build";
	    $platLabels = $this->generateCrashesByBuild($platforms, $builds);
	  
	  }else{
            $crashGraphLabel = "Crashes By OS";
	    $platLabels = $this->generateCrashesByOS($platforms, $builds);
	  }

	  $buildTicks = array();
          $index = 0;
	  for($i = count($builds) - 1; $i  >= 0 ; $i = $i - 1){
	    $buildTicks[] = array($index, date('m/d', strtotime($builds[$i]->build_date)));
            $index += 1;
	  }
	  $bug_model = new Bug_Model;
          $rows = $bug_model->bugsForSignatures(array($params['signature']));
	  $bugzilla = new Bugzilla;
	  $signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));

          $this->setViewData(array(
            'params'  => $params,
            'queryTooBroad' => $helper->shouldShowWarning(),
            'reports' => $reports,
            'builds'  => $builds,

            'all_products'  => $branch_data['products'],
            'all_branches'  => $branch_data['branches'],
            'all_versions'  => $branch_data['versions'],
            'all_platforms' => $platforms,

            'crashGraphLabel' => $crashGraphLabel,
            'platformLabels'  => $platLabels,
	    'buildTicks'      => $buildTicks,

            'sig2bugs' => $signature_to_bugzilla
          ));
	}
    }

    private function generateCrashesByBuild($platforms, $builds){
      $platLabels = array();
      foreach ($platforms as $platform){
	$plotData = array();
        $index = 0;
	for($i = count($builds) - 1; $i  >= 0; $i = $i - 1){
	  $plotData[] = array($index, $builds[$i]->{"count_$platform->id"});
          $index += 1;
	}
	$platLabels[] = array("label" => substr($platform->name, 0, 3),
			      "data"  => $plotData,
			      "color" => $platform->color);
	}
      return $platLabels;
    }

    private function generateCrashesByOS($platforms, $builds){
        $platLabels = array();
        $plotData =   array();
	
        for($i = 0; $i < count($platforms); $i += 1){
          $platform = $platforms[$i];
          $plotData[$platform->id] = array($i, 0);
          for($j = 0; $j  < count($builds); $j = $j + 1){ 
            $plotData[$platform->id][1] += intval($builds[$j]->{"count_$platform->id"});
	  }
          $platLabels[] = array("label" => substr($platform->name, 0, 3),
				"data" => array($plotData[$platform->id]),
                                "color" => $platform->color);
        }
	return $platLabels;
    }

    /**
     * Fetch and display a single report.
     */
    public function index($id) {
        $crash = new Crash();
        $uuid = $crash->parseUUID($id);
        if ($uuid == FALSE ) {
            return Event::run('system.404');
        }

        $crashDirs = Kohana::config('application.dumpPaths');
	foreach ($crashDirs as $crashDir) {
          $report = $this->report_model->getByUUID($uuid, $crashDir);
	  if ($this->report_model->exists($uuid, $crashDir)) {
	    break;
	  }
	}


        if ( is_null($report)) {
            if (!isset($_GET['p'])) {
                $this->priorityjob_model = new Priorityjobs_Model();
                $this->priorityjob_model->add($uuid);
            }
	    return url::redirect('report/pending/'.$uuid);
        } else {
            cachecontrol::set(array(
                'etag'          => $uuid,
                'last-modified' => strtotime($report->date_processed)
            ));
	    $report->sumo_signature = $this->_makeSumoSignature($report->signature);
            $reportJsonZUri = url::file('dumps/' . $uuid . '.jsonz');

	    $bug_model = new Bug_Model;
            $rows = $bug_model->bugsForSignatures(array($report->signature));
	    $bugzilla = new Bugzilla;
	    $signature_to_bugzilla = $bugzilla->signature2bugzilla($rows, Kohana::config('codebases.bugTrackingUrl'));

            $this->setViewData(array(
                'reportJsonZUri' => $reportJsonZUri,
                'report' => $report,
                'branch' => $this->branch_model->getByProductVersion($report->product, $report->version),
		'sig2bugs' => $signature_to_bugzilla
            ));
	}
    }

    /**
     * Wait while a pending job is processed.
     */
    public function pending($id) {
        $crash = new Crash();
        $uuid = $crash->parseUUID($id);
        if ($uuid == FALSE) {
            Kohana::log('alert', "Improper UUID format for $uuid doing 404");
            return Event::run('system.404');
        }
        $crashDirs = Kohana::config('application.dumpPaths');
	foreach ($crashDirs as $crashDir) {
	  if ($this->report_model->exists($uuid, $crashDir)) {
	    $report = $this->report_model->getByUUID($uuid, $crashDir);
	    if ($report) {
	        $this->setAutoRender(FALSE);
                return url::redirect('report/index/'.$uuid);
		break;
	    } 

	  }
	  
	}
        
        $this->job_model = new Job_Model();
        $job = $this->job_model->getByUUID($uuid);

        $this->setViewData(array(
            'uuid' => $uuid,
            'job'  => $job
        ));
    }

    /**
     * Linking reports with ID validation.
     *
     * This method should not touch the database!
     */
    public function find() {
        $crash = new Crash();
        $id = isset($_GET['id']) ? $_GET['id'] : '';
        $uuid = $crash->parseUUID($id);

        if ($uuid) {
            return url::redirect('report/index/'.$uuid);
        } else {
            return url::redirect('');
        }
    }

    private function _makeSumoSignature($signature) {
        $memory_addr = strpos($signature, '@');
        if ($memory_addr === FALSE) {
	    return $signature;
        } else {
	  return substr($signature, 0, $memory_addr);
        }
    }
}
