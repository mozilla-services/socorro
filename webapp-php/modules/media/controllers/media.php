<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Handles loading of site resources (CSS, JS, images) using Views.
 * By default it is assumed that your media files will be stored in
 * `application/views/media`.
 *
 * Usage:
 *  `http://example.com/index.php/media/css/styles.css`
 *
 * $Id: media.php 3281 2008-08-06 16:13:58Z Shadowhand $
 *
 * @package	   Media Module
 * @author	   Greg MacLellan
 * @copyright  (c) 2007-2008 Kohana Team
 * @license	   http://kohanaphp.com/license.html
 */
class Media_Controller extends Controller {

	protected $separator = FALSE;

	protected $use_cache = FALSE;
	protected $cache_lifetime;

	protected $pack_css = FALSE;
	protected $pack_js = FALSE;

	public function __construct()
	{
		parent::__construct();

		$this->separator = Kohana::config('media.separator') OR $this->separator = ',';

		$cache = Kohana::config('media.cache');
		$this->use_cache = ($cache > 0);

		if (is_int($cache))
		{
			$this->cache_lifetime = $cache;
		}
		else
		{
			$this->cache_lifetime = Kohana::config('cache.lifetime') OR $this->cache_lifetime = 1800;
		}

		if ($this->use_cache AND ! isset($this->cache))
		{
			$this->cache = new Cache;
		}

		$this->pack_css = (bool) Kohana::config('media.pack_css');
		$this->pack_js = Kohana::config('media.pack_js');
		($this->pack_js === TRUE) AND $this->pack_js = 'Normal';
	}

	public function css()
	{
		$querystr = implode('/', $this->uri->argument_array());

		// Find all the individual files
		$files = explode($this->separator, $querystr);

		$mimetype = Kohana::config('mimes.css');
		$mimetype = (isset($mimetype[0])) ? $mimetype[0] : 'text/css';

		$this->use_cache AND $output = $this->cache->get('media.css.'.$querystr);

		if ( ! isset($output) OR empty($output))
		{
			$output = '';
			$filedata = $this->_load_filedata($files, 'css');

			foreach ($filedata as $filename=>$data)
			{
			    $output .= $data;
			}

			if ($this->pack_css)
			{
				$output = $this->css_compress($output);
			}

			($this->use_cache) AND $this->cache->set('media.css.'.$querystr, $data, array('media'), $this->cache_lifetime);
		}

		$mimetype AND header('Content-Type: '.$mimetype);
		echo $output;
	}

	public function js()
	{
		$querystr = implode('/', $this->uri->argument_array());

		// Find all the individual files
		$files = explode($this->separator, $querystr);

		$mimetype = Kohana::config('mimes.js');
		$mimetype = (isset($mimetype[0])) ? $mimetype[0] : 'application/x-javascript';

		$this->use_cache AND $output = $this->cache->get('media.js.'.$querystr);

		if ( ! isset($output) OR empty($output))
		{
			$output = '';
			$filedata = $this->_load_filedata($files, 'js');

			foreach ($filedata as $filename=>$data)
			{
				$output .= $data;
			}

			if ($this->pack_js)
			{
				$output = $this->_js_compress($output);
			}

			($this->use_cache) AND $this->cache->set('media.js.'.$querystr, $data, array('media'), $this->cache_lifetime);
		}

		$mimetype AND header('Content-Type: '.$mimetype);
		echo $output;
	}

	public function __call($method, $args)
	{
		$segments = $this->uri->argument_array();

		$filename = array_pop($segments);
		$type = implode('/',$segments);

		if (($pos = strrpos($filename, '.')) !== FALSE)
		{
			$extension = substr($filename, $pos + 1);
			$filename = substr($filename, 0, $pos);
		}
		else
		{
			$extension = '';
		}

		try
		{
			echo View::factory('media/'.$type.'/'.$filename, NULL, $extension)->render();
		}
		catch (Kohana_Exception $exception)
		{
			Event::run('system.404');
		}
	}

	public function _load_filedata($files, $resource_type)
	{
		$filedata = array();

		foreach ($files as $orig_filename)
		{
			$filename = $orig_filename;
			if (substr($filename, -1 * strlen($resource_type) - 1) == '.'.$resource_type)
			{
				$filename = substr($filename, 0, -1 * strlen($resource_type) - 1);
			}

			try
			{
				$view = new View('media/'.$resource_type.'/'.$filename, null, $resource_type);
			}
			catch (Kohana_Exception $exception)
			{
				// try to load the file as a php view (eg, file.css.php)
				try
				{
					$view = new View('media/'.$resource_type.'/'.$orig_filename);
				}
				catch (Kohana_Exception $exception)
				{
					// not found
					unset($view);
				}
			}

			(isset($view)) AND $filedata[$filename] = $view->render();
		}

		return $filedata;
	}

	public function css_compress($data)
	{
		// Remove comments
		$data = preg_replace('~/\*[^*]*\*+([^/][^*]*\*+)*/~', '', $data);

		// Replace all whitespace by single spaces
		$data = preg_replace('~\s+~', ' ', $data);

		// Remove needless whitespace
		$data = preg_replace('~ *+([{}+>:;,]) *~', '$1', trim($data));

		// Remove ; that closes last property of each declaration
		$data = str_replace(';}', '}', $data);

		// Remove empty CSS declarations
		$data = preg_replace('~[^{}]++\{\}~', '', $data);

		return $data;
	}

	public function _js_compress($data)
	{
		$packer = new JavaScriptPacker($data, $this->pack_js);
		return $packer->pack();
	}

} // End Media_Controller
