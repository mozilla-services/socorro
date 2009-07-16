<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Custom controller subclass used throughout application
 */
set_include_path(APPPATH . 'vendor' . PATH_SEPARATOR . get_include_path());

require_once(Kohana::find_file('libraries', 'MY_QueryFormHelper', TRUE, 'php'));
require_once(Kohana::find_file('libraries', 'socorro_cookies', TRUE, 'php'));

class Controller extends Controller_Core {

    // Wrapper layout for current view
    protected $layout = 'layout';

    // Wrapped view for current method
    protected $view = FALSE;

    // Automatically render the layout?
    protected $auto_render = TRUE;

    // Variables for templates
    protected $view_data;

    // Track the global "Chosen" version
    // This changes as user navigates Socorro UI
    protected $chosen_version;

    /**
     * Constructor.
     */
    public function __construct()
    {
        parent::__construct();

        // Create instances of the commonly used models.
        $this->common_model   = new Common_Model();
        $this->branch_model   = new Branch_Model();
        $this->report_model   = new Report_Model();
        $this->platform_model = new Platform_Model();

        // Start with empty set of view vars.
        $this->view_data = array(
            'controller' => $this
        );

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
            $value = rawurldecode($value);
            if (isset($params[$name])) {
                $params[$name][] = $value;
            } else {
                $params[$name] = array( $value );
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

    protected function setNavigationData()
    {
        $curProds = $this->currentProducts();
        $this->setViewData('common_products', $curProds);

	$this->ensureChosenVersion($curProds);
	$this->setViewData('chosen_version', $this->chosen_version);
    }

    private $_current_products;
    protected function currentProducts()
    {
        if (is_null($this->_current_products)) {
            $queryFormHelper = new QueryFormHelper;
	    $p2vs = $queryFormHelper->prepareAllProducts($this->branch_model);
 	    $this->_current_products = $queryFormHelper->currentProducts($p2vs['products2versions']);
	}
	return $this->_current_products;
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
        $view = new View(Router::$controller . '/' . Router::$method . '_csv');
        $view->set_global($this->getViewData());
	echo $view->render();
    }

    protected function navigationChooseVersion($product, $version, $release=NULL)
    {
        if (is_null($release)) {
  	    $determine = new Release;
	    $release = $determine->typeOfRelease($version);
        }
	$this->ensureChosenVersion($this->currentProducts());
	if ($this->chosen_version['version'] != $version ||
	    $this->chosen_version['product'] != $product) {
	        $this->_chooseVersion(array('product' => $product,
					    'version' => $version,
					    'release' => $release));
	} else {
	  //no op, it's already chosen
	  Kohana::log('debug', "Same $product $version skipping " . Kohana::debug($this->chosen_version));
	}
    }

    private function _chooseVersion($version_info, $set_cookie=TRUE)
    {
        $this->chosen_version = $version_info;
	$product = $version_info['product'];
	$version = $version_info['version'];
	$release = $version_info['release'];
	cookie::set(Socorro_Cookies::CHOSEN_VERSION, 
		    "p=${product}&v=${version}&r=${release}", 
		    Socorro_Cookies::EXPIRES_IN_A_YEAR);
    }

    protected function ensureChosenVersion($curProds)
    {
        // if it's null, use Cookie
        if (is_null($this->chosen_version)) {
	    $cv = cookie::get(Socorro_Cookies::CHOSEN_VERSION);
	    if (is_null($cv)) {
	        foreach ($curProds as $product => $releases) {

		    foreach (array_reverse($releases) as $release => $version) {
		        $this->_chooseVersion(array('product' => $product,
						    'version' => $version,
						    'release' => $release));
			break;
		    }
		    break;
		}
	    } else {
	        $version_info = array();
		parse_str($cv, $version_info);
		$this->_chooseVersion(array('product' => $version_info['p'],
					    'version' => $version_info['v'],
					    'release' => $version_info['r']), FALSE);
	    }
        }
    }
}
