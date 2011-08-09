<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Forge module demo controller. This controller should NOT be used in production.
 * It is for demonstration purposes only!
 *
 * $Id: forge_demo.php 2314 2008-03-18 01:00:13Z Shadowhand $
 *
 * @package    Forge
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Forge_demo_Controller extends Controller {

	// Do not allow to run in production
	const ALLOW_PRODUCTION = FALSE;

	public function index()
	{
		$profiler = new Profiler;

		$foods = array
		(
			'tacos' => array('tacos', FALSE),
			'burgers' => array('burgers', FALSE),
			'spaghetti' => array('spaghetti (checked)', TRUE),
			'cookies' => array('cookies (checked)', TRUE),
		);

		$form = new Forge(NULL, 'New User');

		// Create each input, following this format:
		//
		//   type($name)->attr(..)->attr(..);
		//
		$form->hidden('hideme')->value('hiddenz!');
		$form->input('email')->label(TRUE)->rules('required|valid_email');
		$form->input('username')->label(TRUE)->rules('required|length[5,32]');
		$form->password('password')->label(TRUE)->rules('required|length[5,32]');
		$form->password('confirm')->label(TRUE)->matches($form->password);
		$form->checkbox('remember')->label('Remember Me');
		$form->checklist('foods')->label('Favorite Foods')->options($foods)->rules('required');
		$form->dropdown('state')->label('Home State')->options(locale_US::states())->rules('required');
		$form->dateselect('birthday')->label(TRUE)->minutes(15)->years(1950, date('Y'));
		$form->submit('Save');

		if ($form->validate())
		{
			echo Kohana::debug($form->as_array());
		}

		echo $form->render();

		// Using a custom template:
		// echo $form->render('custom_view', TRUE);
		// Inside the view access the inputs using $input_id->render(), ->label() etc
		//
		// To get the errors use $input_id_errors.
		// Set the error format with $form->error_format('<div>{message}</div>');
		// Defaults to <p class="error">{message}</p>
		//
		// Examples:
		//   echo $username->render(); echo $password_errors;
	}

	public function upload()
	{
		$profiler = new Profiler;

		$form = new Forge;
		$form->input('hello')->label(TRUE);
		$form->upload('file', TRUE)->label(TRUE)->rules('required|size[200KB]|allow[jpg,png,gif]');
		$form->submit('Upload');

		if ($form->validate())
		{
			echo Kohana::debug($form->as_array());
		}

		echo $form->render();
	}

} // End Forge Demo Controller
