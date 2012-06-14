/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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

        $uri = $this->buildURI($params, 'search');
        $res = $this->service->get($uri);
        //echo '<pre>',var_dump($uri),'</pre>';
        return $res;
    }

    private function buildURI($params, $apiEntry)
    {
        $separator = '/';
        $apiData = array(
            Kohana::config('webserviceclient.socorro_hostname'),
            $apiEntry,
            'signatures',
        );

        //echo '<pre>',var_dump($params),'</pre>';

        foreach ($params as $key => $value)
        {
            if (!empty($value))
            {
                // Be sure to add the value only if we know the param and we added a key for it
                $unknownParam = false;

                switch ($key)
                {
                    case 'query':
                        $apiData[] = 'for';
                        break;
                    case 'query_search':
                        $apiData[] = 'in';
                        break;
                    case 'product':
                        $apiData[] = 'products';
                        $value = implode('+', $value);
                        break;
                    case 'version':
                        $apiData[] = 'versions';
                        $value = implode('+', $value);
                        break;
                    case 'query_type':
                        $apiData[] = 'search_mode';
                        switch ($value)
                        {
                            case 'startswith':
                                $value = 'starts_with';
                                break;
                            case 'exact':
                                $value = 'is_exactly';
                                break;
                        }
                        break;
                    case 'date':
                        $apiData[] = 'to';
                        $value = date( 'Y-m-d H:i:s', strtotime($value) );
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
                            $value = date('Y-m-d H:i:s', $diff);
                        }
                        break;
                    case 'platform':
                        $apiData[] = 'os';
                        $value = implode('+', $value);
                        break;
                    case 'reason':
                        $apiData[] = 'reasons';
                        break;
                    case 'branch':
                        $apiData[] = 'branches';
                        $value = implode('+', $value);
                        break;
                    case 'build_id':
                        $apiData[] = 'build_ids';
                        break;
                    case 'hang_type':
                        $apiData[] = 'report_type';
                        break;
                    case 'process_type':
                        $apiData[] = 'report_process';
                        break;
                    case 'plugin_field':
                        $apiData[] = 'plugin_in';
                        break;
                    case 'plugin_query_type':
                        $apiData[] = 'plugin_search_mode';
                        switch ($value)
                        {
                            case 'startswith':
                                $value = 'starts_with';
                                break;
                            case 'exact':
                                $value = 'is_exactly';
                                break;
                        }
                        break;
                    case 'plugin_query':
                        $apiData[] = 'plugin_terms';
                        break;
                    case 'result_offset':
                        $apiData[] = 'result_offset';
                        break;
                    case 'result_number':
                        $apiData[] = 'result_number';
                        break;
                    case 'force_api_impl':
                        $apiData[] = 'force_api_impl';
                        break;
                    default:
                        $unknownParam = true;
                }

                if (!$unknownParam)
                {
                    // Securing encoded "/" because of Apache refusing them in URIs
                    $value = str_replace('/', '%2F', $value);
                    $apiData[] = rawurlencode($value);
                }
            }
        }

        $apiData[] = '';    // Trick to have the closing '/'

        return implode($separator, $apiData);
    }

}
