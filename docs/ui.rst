.. index:: ui

.. _ui-chapter:

Socorro UI
==========

The Socorro UI is a KohanaPHP implementation that will operate the
frontend website for the Crash Reporter website.

Coding Standards
----------------

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
------------------

Here is an example of a new report which uses a web service to fetch data
(JSON via HTTP) and displays the result as an HTML table.

Kohana uses the Model-View-Controller (MVC) pattern:
http://en.wikipedia.org/wiki/Model-view-controller

Create model, view(s) and controller for new report (substituting "newreport"
for something more appropriate):

Configuration (optional)
^^^^^^^^^^^^^^^^^^^^^^^^
webapp-php/application/config/new_report.php

.. code-block:: php

    <?php defined('SYSPATH') OR die('No direct access allowed.');
    
    // The number of rows to display.
    $config['numberofrows'] = 20;
    
    // The number of results to display on the by_version page.
    $config['byversion_limit'] = 300;
    ?>


Model
^^^^^
webapp-php/application/models/newreport.php

See :ref:`addaservice-chapter` for details about writing a middleware service for
this to use.

.. code-block:: php

    <?php
    class NewReport_Model extends Model {
        public function getNewReportViaWebService() {
            // this should be pulled from the middleware service
        }
    }
    ?>

View
^^^^
webapp-php/application/views/newreport/byversion.php

.. code-block:: html+php

    <?php slot::start('head') ?>
    <title>New Report for <?php out::H($product) ?> <?php out::H($version) ?></title>
    <?php echo html::script(array(
           'js/path/to/scripts/you/need.js'
        ))?>
    <?php echo html::stylesheet(array(
            'css/path/to/css/you/need.css'
        ), 'screen')?>
    <?php slot::end() ?>
    <!-- Your custom front end HTML goes here -->

Controller
^^^^^^^^^^
webapp-php/application/controllers/newreport.php

.. code-block:: php

    <?php defined('SYSPATH') or die('No direct script access.');
    require_once(Kohanna::find_file('libraries', 'somelib', TRUE 'php'));
        
    class NewReport_Controller extends Controller {
        
        public function __construct() {
            parent::__construct();
            $this->newreport_model = new NewReport_Model();
        }
            
        // Public functions map to routes on the controller
        // http://<base-url>/NewReport/index/[product, version, ?'foo'='bar', etc]
        public function index() {
            $resp = $this->newreport_model->getNewReportViaWebService();
            if ($resp) {
                $this->setViewData(array(
                    'resp' => $resp,
                    'nav_selection' => 'new_report',
                    'foo' => $resp->foo,
                ));
            } else {
                header("Data access error", TRUE, 500);
                $this->setViewData(array(
                    'resp' => $resp,
                    'nav_selection' => 'new_report',
                ));
            }
        }
        
    }
    ?>
