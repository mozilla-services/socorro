<?php
/**
 * Management of data in the priorityjobs table.
 */
class Priorityjobs_Model extends Model {

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
     * Add a new priority job by UUID
     *
     * @param  string The UUID of the report in question
     * @return mixed  Result of the DB insert
     */
    public function add($uuid) {
        // Check for an existing UUID, and only insert if none found.
        $url = Kohana::config('webserviceclient.socorro_hostname') . '/priorityjobs/uuid/' . rawurlencode($uuid) . '/';
        $jobs = $this->service->get($url);
        if (isset($jobs->total) && $jobs->total == 0) {
            return $this->service->post($url);
        }
    }

}
