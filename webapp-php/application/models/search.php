<?php defined('SYSPATH') or die('No direct script access.');

/**
 * Common model class managing the search API calls.
 */
class Search_Model extends Model {

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

    public function search($params, $result_number, $result_offset)
    {
        $params['result_number'] = $result_number;
        $params['result_offset'] = $result_offset;

        $uri = $this->buildURI($params, '201105', 'search');
        $res = $this->service->get($uri);
        //echo '<pre>',var_dump($uri),'</pre>';
        return $res;
    }

    private function buildURI($params, $apiVersion, $apiEntry)
    {
        $separator = '/';
        $apiData = array(
            Kohana::config('webserviceclient.socorro_hostname'),
            $apiVersion,
            $apiEntry,
            'signatures',
        );

        //echo '<pre>',var_dump($params),'</pre>';

        foreach ($params as $key => $value)
        {
            if (!empty($value))
            {
                switch ($key)
                {
                    case 'query':
                        $apiData[] = 'for';
                        $apiData[] = urlencode($value);
                        break;
                    case 'query_search':
                        $apiData[] = 'in';
                        $apiData[] = urlencode($value);
                        break;
                    case 'product':
                        $apiData[] = 'product';
                        $apiData[] = urlencode(implode('+', $value));
                        break;
                    case 'version':
                        $apiData[] = 'version';
                        $apiData[] = urlencode(implode('+', $value));
                        break;
                    case 'query_type':
                        $apiData[] = 'search_mode';
                        switch ($value)
                        {
                            case 'startswith':
                                $apiData[] = 'starts_with';
                                break;
                            case 'exact':
                                $apiData[] = 'is_exactly';
                                break;
                            default:
                                $apiData[] = urlencode($value);
                        }
                        break;
                    case 'date':
                        $apiData[] = 'to';
                        $formattedDate = date( 'Y-m-d H:i:s', strtotime($value) );
                        $apiData[] = urlencode( $formattedDate );
                        break;
                    case 'range_value':
                        if (!empty($params['range_unit']))
                        {
                            $apiData[] = 'from';

                            // Building the from_date given a number of weeks, days or hours.
                            $fromDate = isset($params['date']) ? strtotime($params['date']) : time();
                            switch ($params['range_unit'])
                            {
                                case 'hours':
                                    $diff = strtotime( '-'.$value.' hours', $fromDate );
                                    break;
                                case 'days':
                                    $diff = strtotime( '-'.$value.' days', $fromDate );
                                    break;
                                case 'weeks':
                                default:
                                    $diff = strtotime( '-'.$value.' weeks', $fromDate );
                                    break;
                            }

                            $apiData[] = urlencode( date('Y-m-d H:i:s', $diff) );
                        }
                        break;
                    case 'platform':
                        $apiData[] = 'os';
                        $apiData[] = urlencode(implode('+', $value));
                        break;
                    case 'reason':
                        $apiData[] = 'reason';
                        $apiData[] = urlencode($value);
                        break;
                    case 'branch':
                        $apiData[] = 'branches';
                        $apiData[] = urlencode(implode('+', $value));
                        break;
                    case 'build_id':
                        $apiData[] = 'build';
                        $apiData[] = urlencode($value);
                        break;
                    case 'hang_type':
                        $apiData[] = 'report_type';
                        $apiData[] = urlencode($value);
                        break;
                    case 'process_type':
                        $apiData[] = 'report_process';
                        $apiData[] = urlencode($value);
                        break;
                    case 'plugin_field':
                        $apiData[] = 'plugin_in';
                        $apiData[] = urlencode($value);
                        break;
                    case 'plugin_query_type':
                        $apiData[] = 'plugin_search_mode';
                        $apiData[] = urlencode($value);
                        break;
                    case 'plugin_query':
                        $apiData[] = 'plugin_term';
                        $apiData[] = urlencode($value);
                        break;
                    case 'result_offset':
                        $apiData[] = 'result_offset';
                        $apiData[] = urlencode($value);
                        break;
                    case 'result_number':
                        $apiData[] = 'result_number';
                        $apiData[] = urlencode($value);
                        break;
                }
            }
        }

        $apiData[] = '';    // Trick to have the closing '/'

        return implode($separator, $apiData);
    }

}
