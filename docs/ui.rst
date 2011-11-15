.. index:: ui

.. _ui-chapter:

Socorro UI
==========

The Socorro UI is a KohanaPHP implementation that will operate the
frontend website for the Crash Reporter website.
Coding Standards

Maintaining coding standards will encourage current developers and
future developers to implement clean and consistent code throughout
the codebase.

The PEAR Coding Standards
(http://pear.php.net/manual/en/standards.php) will serve as the basis
for the Socorro UI coding standards.

* Always include header documentation for each class and each method.
    * When updating a class or method that does not have header
      documentation, add header documentation before committing.
    * Header documentation should be added for all methods within
      each controller, model, library and helper class.
    * @param documentation is required for all parameters
    * Header documentation should be less than 80 characters
      in width.
* Add inline documentation for complex logic within a method.
* Use 4 character tab indentations for both PHP and Javascript
* Method names must inherently describe the functionality within that method.
    * Method names must be written in a camel-case format. e.g. getThisThing
    * Method names should follow the verb-noun format, such as a getThing, editThing, etc.
* Use carriage returns in if statements containing more than 2
  statements and in arrays containing more than 3 array members for
  readability.
* All important files, such as controllers, models and libraries,
  must have the Mozilla Public License at the top of the file.

Adding new reports
-----------

Here is an example of a new report which uses a web service to fetch data
(JSON via HTTP) and displays the result as an HTML table.

Kohana uses the Model-View-Controller (MVC) pattern:
http://en.wikipedia.org/wiki/Model-view-controller

Create model, view(s) and controller for new report (substituting "newreport"
for something more appropriate):

Configuration (optional)
^^^^^^^^^^^^
webapp-php/application/config/new_report.php

.. code-block:: php

    <?php defined('SYSPATH') OR die('No direct access allowed.');
    
    // The number of rows to display.
    $config['numberofrows'] = 20;
    
    // The number of results to display on the by_version page.
    $config['byversion_limit'] = 300;
    ?>


Model
^^^^^^^^^^^^
webapp-php/application/models/newreport.php

.. code-block:: php

    <?php 
    class NewReport_Model extends Model {
        public function getNewReportViaWebService($product, $version, $duration, $page)
        {
           $config = array();
           $credentials = Kohana::config('webserviceclient.basic_auth');
           if ($credentials) {
               $config['basic_auth'] = $credentials;
           }
           $service = new Web_Service($config); 
           $host = Kohana::config('webserviceclient.socorro_hostname'); 
           $cache_in_minutes = Kohana::config('webserviceclient.new_report_cache_minutes', 60);
           $end_date = urlencode(date('Y-m-d\TH:i:s\T+0000', TimeUtil::roundOffByMinutes($cache_in_minutes)));
           $limit = Kohana::config('new_report.byversion_limit', 300);
           $lifetime = Kohana::config('products.cache_expires');
           $p = urlencode($product);
           $v = urlencode($version);
           $pg = urlencode($page);
        
           $resp = $service->get("${host}/reports/new/p/${p}/v/${v}/end/${end_date}/duration/${duration}/listsize/${limit}/page/${pg}");
           if($resp) {
               return $resp;
           } 
           return false;
        }
    }
    ?>

View
^^^^^^^^^^^^
webapp-php/application/views/newreport/byversion.php

.. code-block:: html+php

    <?php slot::start('head') ?>
        <title>New Report for <?php out::H($product) ?> <?php out::H($version) ?></title>
        <?php echo html::script(array(
           'js/jquery/plugins/ui/jquery.tablesorter.min.js',
           'js/jquery/plugins/jquery.girdle.min.js',
        ))?>
        <?php echo html::stylesheet(array(
            'css/flora/flora.tablesorter.css'
        ), 'screen')?>
    
    <?php slot::end() ?>
    
    <div class="page-heading">
      <h2>New Report for <span class="current-product"><?php out::H($product) ?></span> <span class="current-version"><?php out::H($version) ?></span></h2>
        <ul class="options">
            <li><a href="<?php echo url::base(); ?>newreport/byversion/<?php echo $product ?>/<?php echo $version ?>" class="selected">By Product/Version</a></li>
        </ul>
        <ul class="options">
          <li><a href="<?php out::H($url_base); ?>?duration=3" <?php if ($duration == 3) echo ' class="selected"'; ?>>3 days</a></li>
          <li><a href="<?php out::H($url_base); ?>?duration=7" <?php if ($duration == 7) echo ' class="selected"'; ?>>7 days</a></li>
          <li><a href="<?php out::H($url_base); ?>?duration=14" <?php if ($duration == 14) echo ' class="selected"'; ?>>14 days</a></li>
        </ul>
    </div>
    
    
    <div class="panel">
      <div class="body notitle">
        <table id="signatureList" class="tablesorter">
          <thead>
            <tr>
              <th class="header">Browser Signature</th>
              <th class="header">Plugin Signature</th>
              <th class="header">Flash Version</th>
              <th class="header">OOID</th>
              <th class="header">Report Day</th>
            </tr>
          </thead>
          <tbody>
    <?php
    if ($resp) {
        View::factory('moz_pagination/nav')->render(TRUE);
        foreach ($resp->newReport as $entry) {
            $sigParams = array(
                'date'        => $entry->report_day,
                'signature'   => $entry->browser_signature
            );
            if (property_exists($entry, 'branch')) {
                $sigParams['branch'] = $entry->branch;
            } else {
                $sigParams['version'] = $product . ':' . $version;
            }
    
            $browser_link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
            $sigParams['signature'] = $entry->plugin_signature;
            $plugin_link_url =  url::base() . 'report/list?' . html::query_string($sigParams);
            $uuid_link_url = url::base() . 'report/index/' . $entry->uuid;
    ?>
            <tr>
              <td>
                <a href="<?php out::H($browser_link_url) ?>" class="signature signature-preview"><?php out::H($entry->browser_signature) ?></a>
              </td>
              <td>
                <a href="<?php out::H($plugin_link_url) ?>" class="signature signature-preview"><?php out::H($entry->plugin_signature) ?></a>
              </td>
              <td>
                <?php out::H($entry->flash_version) ?>
              </td>
              <td>
                <a href="<?php out::H($uuid_link_url)?>"><?php out::H($entry->uuid) ?></a>
              </td>
              <td>
                <?php out::H($entry->report_day) ?>
              </td>
            </tr>
    <?php
        }
    ?>
          <tbody>
        </table>
    <?php
        View::factory('moz_pagination/nav')->render(TRUE);
    } else {
        View::factory('common/data_access_error')->render(TRUE);
    }
    ?>
      </div>
    </div>
    ?>

Controller
^^^^^^^^^^^^
webapp-php/application/controllers/newreport.php

.. code-block:: php

    <?php defined('SYSPATH') or die('No direct script access.');
    require_once(Kohana::find_file('libraries', 'timeutil', TRUE, 'php'));

    class NewReport_Controller extends Controller {
           
        public function __construct()
        {  
            parent::__construct();
            $this->newreport_model = new NewReport_Model();
        }  
    
        private function _versionExists($version) {
            if (!$this->versionExists($version)) {
                Kohana::show_404();
            }
        }
    
        public function index() {
            $products = $this->featured_versions;
            $product = null;
    
            if(empty($products)) {
                Kohana::show_404();
            }
    
            foreach($products as $individual) {
                if($individual->release == 'major') {
                    $product = $individual;
                }
            }
    
            if(empty($product)) {
                $product = array_shift($products);
            }
    
            return url::redirect('/newreport/byversion/' . $product->product);
        }

        public function byversion($product=null, $version=null)
        {
            if(is_null($product)) {
              Kohana::show_404();
            }
            $this->navigationChooseVersion($product, $version);
            if (empty($version)) {
                $this->_handleEmptyVersion($product, 'byversion');
            } else {
                $this->_versionExists($version);
            }
    
            $duration = (int)Input::instance()->get('duration');
            if (empty($duration)) {
                $duration = Kohana::config('products.duration');
            }
    
            $page = (int)Input::instance()->get('page');
            $page = (!empty($page) && $page > 0) ? $page : 1;
    
            $config = array();
            $credentials = Kohana::config('webserviceclient.basic_auth');
            if ($credentials) {
                $config['basic_auth'] = $credentials;
            }
            $service = new Web_Service($config);
    
            $host = Kohana::config('webserviceclient.socorro_hostname');
    
            $cache_in_minutes = Kohana::config('webserviceclient.new_report_cache_minutes', 60);
            $end_date = urlencode(date('Y-m-d\TH:i:s\T+0000', TimeUtil::roundOffByMinutes($cache_in_minutes)));
            $limit = Kohana::config('new_report.byversion_limit', 300);
            // lifetime in seconds
            $lifetime = $cache_in_minutes * 60;
    
            $p = urlencode($product);
            $v = urlencode($version);
            $pg = urlencode($page);
            $resp = $this->newreport_model->getNewReportViaWebService($p, $v, $duration, $pg);
    
            if ($resp) {
                $pager = new MozPager(Kohana::config('new_report.byversion_limit'), $resp->totalCount, $resp->currentPage);

                $this->setViewData(array(
                    'resp'           => $resp,
                    'duration'       => $duration,
                    'product'        => $product,
                    'version'        => $version,
                    'nav_selection'  => 'new_report',
                    'end_date'       => $resp->endDate,
                    'url_base'       => url::site('newreport/byversion/'.$product.'/'.$version),
                    'url_nav'        => url::site('products/'.$product),
                    'pager'          => $pager,
                    'totalItemText' => " Results",
                    'navPathPrefix' => url::site('newreport/byversion/'.$product.'/'.$version) . '?duration=' . $duration . '&page=',
                ));
            } else {
                header("Data access error", TRUE, 500);
                $this->setViewData(
                    array(
                       'nav_selection' => 'top_crashes',
                       'product'       => $product,
                       'url_nav'       => url::site('products/'.$product),
                       'version'       => $version,
                       'resp'          => $resp
                    )
                );
            }
        }

         private function _handleEmptyVersion($product, $method) {
            $product_version = $this->branch_model->getRecentProductVersion($product);
            if (empty($product_version)) {
                // If no current major versions are found, grab any available version
                $product_versions = $this->branch_model->getCurrentProductVersionsByProduct($product);
                if (isset($product_versions[0])) {
                    $product_version = array_shift($product_versions);
                }
            }
    
            $version = $product_version->version;
            $this->chooseVersion(
                array(
                'product' => $product,
                'version' => $version,
                'release' => null
                )
            );

            url::redirect('newreport/'.$method.'/'.$product.'/'.$version);
        }
    }
    ?>
