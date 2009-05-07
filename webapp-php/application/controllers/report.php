<?php
require_once dirname(__FILE__).'/../libraries/MY_SearchReportHelper.php';

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
	    'buildTicks'      => $buildTicks
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
    public function index($uuid) {
        // Validate UUID to make sure there aren't any bullshit characters in it.
        if (!preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/', $uuid) ) {
            return Event::run('system.404');
        }

        $crashDir = Kohana::config('application.dumpPath');
	$report = $this->report_model->getByUUID($uuid, $crashDir);

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
            $reportJsonZUri = url::file('dumps/' . $uuid . '.jsonz');

            $this->setViewData(array(
                'reportJsonZUri' => $reportJsonZUri,
                'report' => $report,
                'branch' => $this->branch_model->getByProductVersion($report->product, $report->version)
            ));
	}
    }

    /**
     * Wait while a pending job is processed.
     */
    public function pending($uuid) {
        if (!$uuid || !preg_match('/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/', $uuid)) {
            Kohana::log('alert', "Improper UUID format for $uuid doing 404");
            return Event::run('system.404');
        }
        $crashDir = Kohana::config('application.dumpPath');
        if ($this->report_model->exists($uuid, $crashDir)) {
	    $report = $this->report_model->getByUUID($uuid, $crashDir);
	    if ($report) {
	        $this->setAutoRender(FALSE);
                return url::redirect('report/index/'.$uuid);
	    } else {
	        Kohana::log('alert', "jsonz crash report exists on disk, but the report database says it hasn't been processed $uuid");
	    }            
        } else {
            Kohana::log('info', "jsonz crash report doesn't exist yet $crashDir $uuid");
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
        $id = isset($_GET['id']) ? $_GET['id'] : '';
        $uuid = FALSE;

        if ($id) {
            $matches = array();
            $prefix = Kohana::config('application.dumpIDPrefix');
            if ( preg_match('/^('.$prefix.')?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/', $id, $matches) ) {
                $uuid = $matches[2];
            }
        }

        if ($uuid) {
            return url::redirect('report/index/'.$uuid);
        } else {
            return url::redirect('');
        }
    }
}
