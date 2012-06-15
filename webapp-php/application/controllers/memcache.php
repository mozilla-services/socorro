<?php defined('SYSPATH') or die('No direct script access.');
/**
 * Simple memcache status page.
 */
class Memcache_Controller extends Controller {

    public function __construct()
    {
        parent::__construct();
        $this->cache_config =& Kohana::config('cache_memcache.servers');
        $this->cache_stats = array();
    }

    public function index() {
        cachecontrol::set(array(
            'expires' => time() + (60)
        ));

        if (class_exists('Memcache') && is_array($this->cache_config)) {

            // Just manually set up a dirty connection because I don't want to spend
            // an hour figuring out how to retrieve and use the protected memcache
            // driver object.  *sad face*
            $c = new Memcache;
            foreach ($this->cache_config as $server) {
                $c->addServer($server['host'], $server['port'], $server['persistent'], $server['weight']);
            }
            $this->cache_stats = $c->getExtendedStats();
            $c->close();
            unset($c);
        }

        $this->setViewData('cache_stats', $this->cache_stats);
    }
}
