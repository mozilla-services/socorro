<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Memcache-based Cache driver.
 *
 * $Id: Memcache.php 3160 2008-07-20 16:03:48Z Shadowhand $
 *
 * @package    Cache
 * @author     Kohana Team
 * @copyright  (c) 2007-2008 Kohana Team
 * @license    http://kohanaphp.com/license.html
 */
class Cache_Memcache_Driver implements Cache_Driver {

	// Cache backend object and flags
	protected $backend;

	public function __construct()
	{
		if ( ! extension_loaded('memcache'))
			throw new Kohana_Exception('cache.extension_not_loaded', 'memcache');

		$this->backend = new Memcache;
        $this->flags = Kohana::config('cache_memcache.compression') ? MEMCACHE_COMPRESSED : 0;

        $this->prefix = Kohana::config('cache_memcache.prefix');

		$servers = Kohana::config('cache_memcache.servers');

		foreach ($servers as $server)
		{
			// Make sure all required keys are set
			$server += array('host' => '127.0.0.1', 'port' => 11211, 'persistent' => FALSE, 'weight' => 1);

			// Add the server to the pool
			$this->backend->addServer($server['host'], $server['port'], (bool) $server['persistent'], $server['weight'])
				or Kohana::log('error', 'Cache: Connection failed: '.$server['host']);
		}
	}

	public function find($tag)
	{
		return FALSE;
	}

	public function errorHandler($errno, $errstr)
        {
            Kohana::log('error', $errstr);
        }

	public function get($id)
	{
                set_error_handler(array($this, 'errorHandler'));
                $return = $this->backend->get($this->prefix.$id);
                if($return === FALSE) {
                    $return = NULL;
                }
                restore_error_handler();
                return $return;
	}

	public function set($id, $data, $tags, $lifetime)
	{
		count($tags) and Kohana::log('error', 'Cache: Tags are unsupported by the memcache driver');

		// Memcache driver expects unix timestamp
		if ($lifetime !== 0)
		{
			$lifetime += time();
		}

                set_error_handler(array($this, 'errorHandler'));
		$result = $this->backend->set($this->prefix.$id, $data, $this->flags, $lifetime);
                restore_error_handler();
                return $result;
	}

	public function delete($id, $tag = FALSE)
	{
		if ($id === TRUE)
			return $this->backend->flush();

		if ($tag == FALSE)
			return $this->backend->delete($this->prefix.$id, 0);

		return TRUE;
	}

	public function delete_expired()
	{
		return TRUE;
	}

} // End Cache Memcache Driver
