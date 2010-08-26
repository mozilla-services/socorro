<?php defined('SYSPATH') or die('No direct script access.');

/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Socorro Crash Reporter
 *
 * The Initial Developer of the Original Code is
 * The Mozilla Foundation.
 * Portions created by the Initial Developer are Copyright (C) 2006
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

set_include_path(APPPATH . 'vendor' . PATH_SEPARATOR . get_include_path());
require_once(Kohana::find_file('libraries', 'MY_QueryFormHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'release', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'socorro_cookies', TRUE, 'php'));

/**
 * Custom controller subclass used throughout application
 */
class Controller extends Controller_Core {

    // Available in all controllers and views.  TRUE for Mozilla's deployment of Socorro UI, which
    // is backed by LDAP authentication. FALSE if auth.driver is set to NoAuth.
    protected $auth_is_active = TRUE;

    // Automatically render the layout?
    protected $auto_render = TRUE;

	// CSS inclusion
	protected $css = '';

    // Track the global "Chosen" product and version.  This changes as user navigates Socorro UI.
    protected $chosen_version;

    // Set an array of current products
    protected $current_products;
    
    // Set an array of featured versions for the chosen product.
    public $featured_versions;

	// Javascript inclusion
	protected $js = '';

    // Wrapper layout for current view
    protected $layout = 'layout';

    // Set an array of versions that are not featured for the chosen product.
    public $unfeatured_versions;

    // Wrapped view for current method
    protected $view = FALSE;

    // Variables for templates
    protected $view_data;

    /**
     * Constructor.
     */
    public function __construct()
    {
        parent::__construct();

        // Create instances of the commonly used models.
        $this->branch_model   = new Branch_Model();
        $this->common_model   = new Common_Model();
        $this->report_model   = new Report_Model();
        $this->platform_model = new Platform_Model();

        // Start with empty set of view vars.
        $this->view_data = array(
            'controller' => $this
        );
        
        $this->auth_is_active = Kohana::config('auth.driver', 'NoAuth') != "NoAuth";

        // Grab an array of current products, ensure that 1 is chosen, and grab the featured versions for that product.
        $this->current_products = $this->branch_model->getProducts();
        $this->ensureChosenVersion($this->current_products);
        $this->prepareVersions();
        
        Event::add('system.post_controller_constructor', array($this, '_auth_prep'));

        // Display the template immediately after the controller method
        Event::add('system.post_controller', array($this, '_display'));
    }

    /**
     * The built-in query string parsing in PHP imposes a naming convention for 
     * variables that appear multiple times in a URL. (ie. var[]=1&var[]=2&var[]=3)  
     * This custom parser handles things more naturally.
     *
     * @param string A query string to parse, or if NULL, the request query string is used.
     * @param array  Parsed query string parameters
     */
    function parseQueryString($str=NULL) {
        if ($str===NULL)
            $str = $_SERVER['QUERY_STRING'];

        $params = array();
        $pairs  = explode('&', $str);
        
        foreach ($pairs as $i) {
            if (!$i) continue;
            list($name, $value) = explode('=', $i, 2);
            $value_clean = trim(
                               $this->input->xss_clean(
                                   urldecode($value)));
            if (isset($params[$name])) {
                $params[$name][] = $value_clean;
            } else {
                $params[$name] = array($value_clean);
            }
        }
        return $params;
    }

    /**
     * Assemble an array of the given named parameters, with defaults.
     *
     * @param  array Parameter names and defaults
     * @return array Request parameters, with default values for those not found.
     */
    public function getRequestParameters($params_and_defaults)
    {
        $get = $this->parseQueryString();
        $params = array();
        foreach ($params_and_defaults as $name=>$default) {
            if (isset($get[$name])) {
                $val = is_array($default) ? $get[$name] : array_pop($get[$name]);
            } else {
                $val = $default;
            }

            if ($val !== NULL) $params[$name] = $val;
        }
        return $params;
    }

    /**
     * Set the state of auto rendering at the end of controller method.
     *
     * @param  boolean whether or not to autorender
     * @return object
     */
    public function setAutoRender($state=TRUE)
    {
        $this->auto_render = $state;
        return $this;
    }

    /**
     * Set the name of the wrapper layout to use at rendering time.
     *
     * @param  string name of the layout wrapper view.
     * @return object
     */
    public function setLayout($name)
    {
        $this->layout = $name;
        return $this;
    }

    /**
     * Set the name of the wrapped view to use at rendering time.
     *
     * @param  string name of the view to use during rendering.
     * @return object
     */
    public function setView($name)
    {
        // Prepend path with the controller name, if not already a path.
        if (strpos($name, '/') === FALSE)
            $name = Router::$controller . '/' . $name;
        $this->view = $name;
        return $this;
    }

    /**
     * Sets one or more view variables for layout wrapper and contained view
     *
     * @param  string|array  name of variable or an array of variables
     * @param  mixed         value of the named variable
     * @return object
     */
    public function setViewData($name, $value=NULL)
    {
        if (func_num_args() === 1 AND is_array($name)) {
            // Given an array of variables, merge them into the working set.
            $this->view_data = array_merge($this->view_data, $name);
        } else {
            // Set one variable in the working set.
            $this->view_data[$name] = $value;
        }
        return $this;
    }

    /**
     * Prepare and set the data that will be used by the template navigation.
     *
     * @return void
     */
    protected function setNavigationData()
    {
        $this->setViewData('chosen_version', $this->chosen_version);
        $this->setViewData('current_products', $this->current_products);
        $this->setViewData('current_product_versions', $this->branch_model->getCurrentProductVersions());
        $this->setViewData('featured_versions', $this->featured_versions);
        $this->setViewData('num_other_products', 
            count($this->branch_model->getProducts()) - count(Kohana::config('dashboard.feat_nav_products')));
        $this->setViewData('unfeatured_versions', $this->unfeatured_versions);        
    }

    private $_current_products;
    protected function currentProducts()
    {
        if (is_null($this->_current_products)) {
            $queryFormHelper = new QueryFormHelper;
            $p2vs = $queryFormHelper->prepareAllProducts($this->branch_model);
            $this->_current_products = $queryFormHelper->currentProducts($p2vs);
        }

        // Resort the products array according to product order importance.
        $product_weights = Kohana::config('products.product_weights');
        asort($product_weights);
        
        $products = array();
        foreach($product_weights as $product => $weight) {
            if (isset($this->_current_products[$product])) {
                $products[$product] = $this->_current_products[$product];
            }
        }
        foreach($this->_current_products as $product => $versions) {
            if (!isset($products[$product])) {
                $products[$product] = $versions;
            }
        }

        return $products;
    }

    /**
     * Get one or all view variables.
     *
     * @param string  name of the variable to get, or none for all
     * @return mixed
     */
    public function getViewData($name=FALSE, $default=NULL)
    {
        if ($name) {
            return isset($this->view_data[$name]) ?
                $this->view_data[$name] : $default;
        } else {
            return $this->view_data;
        }
    }

    public function _auth_prep()
    {
	$this->setViewData('auth_is_active', $this->auth_is_active);
    }
   /**
    * Ensure that if a user is authorized for sensitive information
    * that this page is being served over HTTPS. If not, then the
    * user is redirected to a secure version of the page and this current
    * request dies.
    *
    * @param string The current path and query string params to be switched over to the https protocol
    * @return void string exists if a redirect is performed
    */
    public function sensitivePageHTTPSorRedirectAndDie($path)
    {
	if (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS']) {
	    // Cool, this page was requested via https.
	    // no-op
	} else {
	    $secureUrl = url::site($path, Kohana::config('auth.proto'));
	    // For devs without https... don't do this redirect or it would be an infinite loop
	    if (Kohana::config('auth.proto') == 'https') {
		url::redirect($secureUrl);
		exit();
	    } else {
		Kohana::log('alert', "Dev mode, skipping redirect to " . $secureUrl);
	    }
	}
    }

    /**
     * Render a template wrapped in the global layout.
     */
    public function _display()
    {
        // Do nothing if auto_render is false at this point.
        if ($this->auto_render) {

	    $this->setNavigationData();

            // If no view set by this point, default to controller/method 
            // naming convention.
            if (!$this->view) {
                $this->setView(Router::$controller . '/' . Router::$method);
            }

            // If there's a view set, render it first into .
            if ($this->view) {
                // $view = new View($this->view, $this->getViewData());
                $view = new View($this->view);
                $view->set_global($this->getViewData());
                $this->setViewData('content', $view->render());
            }

            if ($this->layout) {
                // Finally, render the layout wrapper to the browser.
                $layout = new View($this->layout);
				$layout->css = $this->css;
				$layout->js = $this->js;
                $layout->set_global($this->getViewData());
                $layout->render(TRUE);
            } else {
                // No layout wrapper, so try outputting the rendered view.
                echo $this->getViewData('content', '');
            }

        }

    }

    /**
     * Render a csv template to the given filenamePrefix.csv
     * This method is mutually exclusive with the default
     * rendering codepath. Instead of autorendering
     * app/view/$controller/$method.php
     * this function will automagicaly render
     * app/view/$controller/$method_csv.php
     *
     * @param String filenamePrefix - Is sent in Content-Disposition Header
     *        as the suggested filename. CSV extension will be automatically added.
     * @return void - renders to browser
     */
    public function renderCSV($filenamePrefix)
    {
        $this->auto_render = FALSE;
	header('Content-type: text/csv; charset=utf-8');
        header("Content-disposition: attachment; filename=${filenamePrefix}.csv");
        $view = new View('common/csv');
        $view->set_global($this->getViewData());
	echo $view->render();
    }

   /**
    * The app has a notion of a "Current release" that you are
    * interested in for global navigation. This is a specific
    * product / version pair. All pages that detect a single 
    * product version should update this value.
    * @param string product
    * @param string version
    * @param string optional release
    * @void
    */
    protected function navigationChooseVersion($product, $version, $release=NULL)
    {
        if (is_null($release)) {
  	    $determine = new Release;
	    $release = $determine->typeOfRelease($version);
        }
	$this->ensureChosenVersion($this->currentProducts(), FALSE);
	if ($this->chosen_version['version'] != $version ||
	    $this->chosen_version['product'] != $product) {
	        $this->chooseVersion(array('product' => $product,
					    'version' => $version,
					    'release' => $release));
	} else {
	  //no op, it's already chosen
	  Kohana::log('debug', "Same $product $version skipping " . Kohana::debug($this->chosen_version));
	}
    }

    /**
     * Manually specify the selected product / version and save to cookie.
     *
     * @param   array  An Array containing the select product, version, release.
     * @param   bool   True to save selection to a cookie; False if not
     * @return  void
     */
    public function chooseVersion($version_info, $set_cookie=TRUE)
    {
        $this->chosen_version = $version_info;
	    $product = $version_info['product'];
	    $version = $version_info['version'];
	    $release = $version_info['release'];
	    if ($set_cookie) {
	        cookie::set(Socorro_Cookies::CHOSEN_VERSION, 
	    		"p=${product}&v=${version}&r=${release}", 
	    		Socorro_Cookies::EXPIRES_IN_A_YEAR);
	    }
    }

    /**
     * Ensure that a product / version has been selected, even if one was not specifically selected.
     *
     * @param   array  An array of current products / versions
     * @param   bool   True to save selection to a cookie; False if not
     * @return  void
     */
    protected function ensureChosenVersion($curProds, $set_cookie=TRUE)
    {
        // if it's null, use Cookie
        if (is_null($this->chosen_version)) {
            $cv = cookie::get(Socorro_Cookies::CHOSEN_VERSION);
            if (is_null($cv)) {
                $defaultProduct = Kohana::config('dashboard.default_product');
                Kohana::log('info', $defaultProduct);
	            if ($defaultProduct && in_array($defaultProduct, $curProds)) {
                    $this->chooseVersion(
                        array(
                            'product' => $defaultProduct,
                            'version' => null,
                            'release' => null
                        ), 
                        $set_cookie
                    );
                } else {
                    foreach ($curProds as $product => $releases) {
                        foreach (array_reverse($releases) as $release => $version) {
                            $this->chooseVersion(
                                array(
                                    'product' => $product,
                                    'version' => $version,
                                    'release' => $release
                                ), 
                                $set_cookie
                            );
                            break;
                        } 
                        break;
                    }
                }
            } else {
                $version_info = array();
                parse_str($cv, $version_info);
                $this->chooseVersion(
                    array(
                        'product' => $version_info['p'],
                        'version' => $version_info['v'],
                        'release' => $version_info['r']
                    ), 
                    FALSE
                );
            }
        }
    }

    /**
     * Prepare the featured and unfeatured versions for the navigation and the controllers.
     * 
     * @return void
     */
    public function prepareVersions()
    {
        $this->featured_versions = $this->branch_model->getFeaturedVersions($this->chosen_version['product']);
        $this->unfeatured_versions = $this->branch_model->getUnfeaturedVersions($this->chosen_version['product'], $this->featured_versions);
    }

}
