<?php

class Job_Model extends Model
{
    /**
     * The Web Service class.
     */
    protected $service = null;

    public function __construct()
    {
        parent::__construct();

        $config = array();
        $credentials = Kohana::config('webserviceclient.basic_auth');
        if ($credentials) {
            $config['basic_auth'] = $credentials;
        }

        $this->service = new Web_Service($config);
    }

    /**
     * Fetch a single job by UUID
     *
     * @param  string UUID by which to look up job
     * @return object job data
     */
    public function getByUUID($uuid)
    {
        $uri = Kohana::config('webserviceclient.socorro_hostname') . '/job/uuid/' . urlencode($uuid);
        $res = $this->service->get($uri);
        if (!$res || !isset($res->total) || $res->total <= 0) {
            return false;
        }
        return $res->hits[0];
    }
}
