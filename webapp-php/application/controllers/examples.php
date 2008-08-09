<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Contains examples of various Kohana library examples. You can access these
 * samples in your own installation of Kohana by going to ROOT_URL/examples.
 * This controller should NOT be used in production. It is for demonstration
 * purposes only!
 *
 * $Id: examples.php 3300 2008-08-08 14:23:57Z OscarB $
 *
 * @package    Core
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Examples_Controller extends Controller {

	// Do not allow to run in production
	const ALLOW_PRODUCTION = FALSE;

	/**
	 * Displays a list of available examples
	 */
	function index()
	{
		// Get the methods that are only in this class and not the parent class.
		$examples = array_diff
		(
			get_class_methods(__CLASS__),
			get_class_methods(get_parent_class($this))
		);

		sort($examples);

		echo "<strong>Examples:</strong>\n";
		echo "<ul>\n";

		foreach ($examples as $method)
		{
			if ($method == __FUNCTION__)
				continue;

			echo '<li>'.html::anchor('examples/'.$method, $method)."</li>\n";
		}

		echo "</ul>\n";
		echo '<p>'.Kohana::lang('core.stats_footer')."</p>\n";
	}

	/**
	 * Demonstrates how to archive a directory. First enable the archive module
	 */
	//public function archive($build = FALSE)
	//{
	//	if ($build === 'build')
	//	{
	//		// Load archive
	//		$archive = new Archive('zip');

	//		// Download the application/views directory
	//		$archive->add(APPPATH.'views/', 'app_views/', TRUE);

	//		// Download the built archive
	//		$archive->download('test.zip');
	//	}
	//	else
	//	{
	//		echo html::anchor(Router::$current_uri.'/build', 'Download views');
	//	}
	//}

	/**
	 * Demonstrates how to parse RSS feeds by using DOMDocument.
	 */
	function rss()
	{
		// Parse an external atom feed
		$feed = feed::parse('http://codeigniter.com/feeds/atom/news/');

		// Show debug info
		echo Kohana::debug($feed);

		echo Kohana::lang('core.stats_footer');
	}

	/**
	 * Demonstrates the Session library and using session data.
	 */
	function session()
	{
		// Gets the singleton instance of the Session library
		$s = Session::instance();

		echo 'SESSID: <pre>'.session_id()."</pre>\n";

		echo '<pre>'.print_r($_SESSION, TRUE)."</pre>\n";

		echo '<br/>{execution_time} seconds';
	}

	/**
	 * Demonstrates how to use the form helper with the Validation libraryfor file uploads .
	 */
	function form()
	{
		// Anything submitted?
		if ($_POST)
		{
			// Merge the globals into our validation object.
			$post = Validation::factory(array_merge($_POST, $_FILES));

			// Ensure upload helper is correctly configured, config/upload.php contains default entries.
			// Uploads can be required or optional, but should be valid
			$post->add_rules('imageup1', 'upload::required', 'upload::valid', 'upload::type[gif,jpg,png]', 'upload::size[1M]');
			$post->add_rules('imageup2', 'upload::required', 'upload::valid', 'upload::type[gif,jpg,png]', 'upload::size[1M]');

			// Alternative syntax for multiple file upload validation rules
			//$post->add_rules('imageup.*', 'upload::required', 'upload::valid', 'upload::type[gif,jpg,png]', 'upload::size[1M]');

			if ($post->validate() )
			{
				// It worked!
				// Move (and rename) the files from php upload folder to configured application folder
				upload::save('imageup1');
				upload::save('imageup2');
				echo 'Validation successfull, check your upload folder!';
			}
			else
			{
				// You got validation errors
				echo '<p>validation errors: '.var_export($post->errors(), TRUE).'</p>';
				echo Kohana::debug($post);
			}
		}

		// Display the form
		echo form::open('examples/form', array('enctype' => 'multipart/form-data'));
		echo form::label('imageup', 'Image Uploads').':<br/>';
		// Use discrete upload fields
		// Alternative syntax for multiple file uploads
		// echo form::upload('imageup[]').'<br/>';

		echo form::upload('imageup1').'<br/>';
		echo form::upload('imageup2').'<br/>';
		echo form::submit('upload', 'Upload!');
		echo form::close();

	}

	/**
	 * Demontrates how to use the Validation library to validate an arbitrary array.
	 */
	function validation()
	{
		// To demonstrate Validation being able to validate any array, I will
		// be using a pre-built array. When you load validation with no arguments
		// it will default to validating the POST array.
		$data = array
		(
			'user' => 'hello',
			'pass' => 'bigsecret',
			'reme' => '1'
		);

		$validation = new Validation($data);

		$validation->add_rules('user', 'required', 'length[1,12]')->pre_filter('trim', 'user');
		$validation->add_rules('pass', 'required')->post_filter('sha1', 'pass');
		$validation->add_rules('reme', 'required');

		$result = $validation->validate();

		var_dump($validation->errors());
		var_dump($validation->as_array());

		// Yay!
		echo '{execution_time} ALL DONE!';
	}

	/**
	 * Demontrates how to use the Captcha library.
	 */
	public function captcha()
	{
		// Look at the counters for valid and invalid
		// responses in the Session Profiler.
		new Profiler;

		// Load Captcha library, you can supply the name
		// of the config group you would like to use.
		$captcha = new Captcha;

		// Ban bots (that accept session cookies) after 50 invalid responses.
		// Be careful not to ban real people though! Set the threshold high enough.
		if ($captcha->invalid_count() > 49)
			exit('Bye! Stupid bot.');

		// Form submitted
		if ($_POST)
		{
			// Captcha::valid() is a static method that can be used as a Validation rule also.
			if (Captcha::valid($this->input->post('captcha_response')))
			{
				echo '<p style="color:green">Good answer!</p>';
			}
			else
			{
				echo '<p style="color:red">Wrong answer!</p>';
			}

			// Validate other fields here
		}

		// Show form
		echo form::open();
		echo '<p>Other form fields here...</p>';

		// Don't show Captcha anymore after the user has given enough valid
		// responses. The "enough" count is set in the captcha config.
		if ( ! $captcha->promoted())
		{
			echo '<p>';
			echo $captcha->render(); // Shows the Captcha challenge (image/riddle/etc)
			echo '</p>';
			echo form::input('captcha_response');
		}
		else
		{
			echo '<p>You have been promoted to human.</p>';
		}

		// Close form
		echo form::submit(array('value' => 'Check'));
		echo form::close();
	}

	/**
	 * Demonstrates the features of the Database library.
	 *
	 * Table Structure:
	 *  CREATE TABLE `pages` (
	 *  `id` mediumint( 9 ) NOT NULL AUTO_INCREMENT ,
	 *  `page_name` varchar( 100 ) NOT NULL ,
	 *  `title` varchar( 255 ) NOT NULL ,
	 *  `content` longtext NOT NULL ,
	 *  `menu` tinyint( 1 ) NOT NULL default '0',
	 *  `filename` varchar( 255 ) NOT NULL ,
	 *  `order` mediumint( 9 ) NOT NULL ,
	 *  `date` int( 11 ) NOT NULL ,
	 *  `child_of` mediumint( 9 ) NOT NULL default '0',
	 *  PRIMARY KEY ( `id` ) ,
	 *  UNIQUE KEY `filename` ( `filename` )
	 *  ) ENGINE = MYISAM DEFAULT CHARSET = utf8 PACK_KEYS =0;
	 *
	*/
	function database()
	{
		$db = new Database;

		$table = 'pages';
		echo 'Does the '.$table.' table exist? ';
		if ($db->table_exists($table))
		{
			echo '<p>YES! Lets do some work =)</p>';

			$query = $db->select('DISTINCT pages.*')->from($table)->get();
			echo $db->last_query();
			echo '<h3>Iterate through the result:</h3>';
			foreach ($query as $item)
			{
				echo '<p>'.$item->title.'</p>';
			}
			echo '<h3>Numrows using count(): '.count($query).'</h3>';
			echo 'Table Listing:<pre>'.print_r($db->list_tables(), TRUE).'</pre>';

			echo '<h3>Try Query Binding with objects:</h3>';
			$sql = 'SELECT * FROM '.$table.' WHERE id = ?';
			$query = $db->query($sql, array(1));
			echo '<p>'.$db->last_query().'</p>';
			$query->result(TRUE);
			foreach ($query as $item)
			{
				echo '<pre>'.print_r($item, true).'</pre>';
			}

			echo '<h3>Try Query Binding with arrays (returns both associative and numeric because I pass MYSQL_BOTH to result():</h3>';
			$sql = 'SELECT * FROM '.$table.' WHERE id = ?';
			$query = $db->query($sql, array(1));
			echo '<p>'.$db->last_query().'</p>';
			$query->result(FALSE, MYSQL_BOTH);
			foreach ($query as $item)
			{
				echo '<pre>'.print_r($item, true).'</pre>';
			}

			echo '<h3>Look, we can also manually advance the result pointer!</h3>';
			$query = $db->select('title')->from($table)->get();
			echo 'First:<pre>'.print_r($query->current(), true).'</pre><br />';
			$query->next();
			echo 'Second:<pre>'.print_r($query->current(), true).'</pre><br />';
			$query->next();
			echo 'Third:<pre>'.print_r($query->current(), true).'</pre>';
			echo '<h3>And we can reset it to the beginning:</h3>';
			$query->rewind();
			echo 'Rewound:<pre>'.print_r($query->current(), true).'</pre>';

			echo '<p>Number of rows using count_records(): '.$db->count_records('pages').'</p>';
		}
		else
		{
			echo 'NO! The '.$table.' table doesn\'t exist, so we can\'t continue =( ';
		}
		echo "<br/><br/>\n";
		echo 'done in {execution_time} seconds';
	}

	/**
	 * Demonstrates how to use the Pagination library and Pagination styles.
	 */
	function pagination()
	{
		$pagination = new Pagination(array(
			// Base_url will default to the current URI
			// 'base_url'    => 'welcome/pagination_example/page/x',

			// The URI segment (integer) in which the pagination number can be found
			// The URI segment (string) that precedes the pagination number (aka "label")
			'uri_segment'    => 'page',

			// You could also use the query string for pagination instead of the URI segments
			// Just set this to the $_GET key that contains the page number
			// 'query_string'   => 'page',

			// The total items to paginate through (probably need to use a database COUNT query here)
			'total_items'    => 254,

			// The amount of items you want to display per page
			'items_per_page' => 10,

			// The pagination style: classic (default), digg, extended or punbb
			// Easily add your own styles to views/pagination and point to the view name here
			'style'          => 'classic',

			// If there is only one page, completely hide all pagination elements
			// Pagination->render() will return an empty string
			'auto_hide'      => TRUE,
		));

		// Just echo to display the links (__toString() rocks!)
		echo 'Classic style: '.$pagination;

		// You can also use the render() method and pick a style on the fly if you want
		echo '<hr /> Digg style:     ', $pagination->render('digg');
		echo '<hr /> Extended style: ', $pagination->render('extended');
		echo '<hr /> PunBB style:    ', $pagination->render('punbb');
		echo 'done in {execution_time} seconds';
	}

	/**
	 * Demonstrates the User_Agent library.
	 */
	function user_agent()
	{
		foreach (array('agent', 'browser', 'version') as $key)
		{
			echo $key.': '.Kohana::user_agent($key).'<br/>'."\n";
		}

		echo "<br/><br/>\n";
		echo 'done in {execution_time} seconds';
	}

	/**
	 * Demonstrates the Payment library.
	 */
	/*function payment()
	{
		$credit_card = new Payment;

		// You can also pass the driver name to the library to use multiple ones:
		$credit_card = new Payment('Paypal');
		$credit_card = new Payment('Authorize');

		// You can specify one parameter at a time:
		$credit_card->login = 'this';
		$credit_card->first_name = 'Jeremy';
		$credit_card->last_name = 'Bush';
		$credit_card->card_num = '1234567890';
		$credit_card->exp_date = '0910';
		$credit_card->amount = '478.41';

		// Or you can also set fields with an array and the <Payment.set_fields> method:
		$credit_card->set_fields(array('login' => 'test',
		                               'first_name' => 'Jeremy',
		                               'last_name' => 'Bush',
		                               'card_num' => '1234567890',
		                               'exp_date' => '0910',
		                               'amount' => '487.41'));

		echo '<pre>'.print_r($credit_card, true).'</pre>';

		echo 'Success? ';
		echo ($response = $credit_card->process() == TRUE) ? 'YES!' : $response;
	}*/

	function calendar()
	{
		$profiler = new Profiler;

		$calendar = new Calendar(8, 2008);
		$calendar->attach($calendar->event()
				->condition('year', 2008)
				->condition('month', 8)
				->condition('day', 8)
				->output(html::anchor('http://forum.kohanaphp.com/comments.php?DiscussionID=275', 'Learning about Kohana Calendar')));

		echo $calendar->render();
	}

	/**
	 * Demonstrates how to use the Image libarary..
	 */
	function image()
	{
		// Application Upload directory
		$dir = realpath(DOCROOT.'upload').'/';

		// Image filename
		$image = DOCROOT.'kohana.png';

		// Create an instance of Image, with file
		// The orginal image is not affected
		$image = new Image($image);

		// Most methods are chainable
		// Resize the image, crop the center left
		$image->resize(200, 100)->crop(150, 50, 'center', 'left');

		// Display image in browser
		$image->render();

		// Save the image
		$image->save($dir.'mypic_thumb.jpg');

		//echo Kohana::debug($image);
	}

	/**
	 * Demonstrates how to use vendor software with Kohana.
	 */
	function vendor()
	{
		// Let's do a little Markdown shall we.
		$br = "\n\n";
		$output = '#Marked Down!#'.$br;
		$output .= 'This **_markup_** is created *on-the-fly*, by ';
		$output .= '[php-markdown-extra](http://michelf.com/projects/php-markdown/extra)'.$br;
		$output .= 'It\'s *great* for user <input> & writing about `<HTML>`'.$br;
		$output .= 'It\'s also good at footnotes :-) [^1]'.$br;
		$output .= '[^1]: A footnote.';

		// looks in system/vendor for Markdown.php
		require Kohana::find_file('vendor', 'Markdown');

		echo Markdown($output);

		echo 'done in {execution_time} seconds';
	}
} // End Examples
