<?php
/**
 * File containing the ezcFeedOnlyOneValueAllowedException class.
 *
 * @package Feed
 * @version 1.2.1
 * @copyright Copyright (C) 2005-2008 eZ systems as. All rights reserved.
 * @license http://ez.no/licenses/new_bsd New BSD License
 * @filesource
 */

/**
 * Thrown when some elements value is not a single value but an array.
 *
 * @package Feed
 * @version 1.2.1
 */
class ezcFeedOnlyOneValueAllowedException extends ezcFeedException
{
    /**
     * Constructs a new ezcFeedOnlyOneValueAllowedException.
     *
     * @param string $attribute The attribute which caused the exception
     */
    public function __construct( $attribute )
    {
        parent::__construct( "The element '{$attribute}' cannot appear more than once." );
    }
}
?>
