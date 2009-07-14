<?php
/**
 * File containing the ezcFeedUnsupportedTypeException class.
 *
 * @package Feed
 * @version 1.2.1
 * @copyright Copyright (C) 2005-2008 eZ systems as. All rights reserved.
 * @license http://ez.no/licenses/new_bsd New BSD License
 * @filesource
 */

/**
 * Thrown when an unsupported feed is created.
 *
 * @package Feed
 * @version 1.2.1
 */
class ezcFeedUnsupportedTypeException extends ezcFeedException
{
    /**
     * Constructs a new ezcFeedUnsupportedTypeException.
     *
     * @param string $type The feed type which caused the exception
     */
    public function __construct( $type )
    {
        parent::__construct( "The feed type '{$type}' is not supported." );
    }
}
?>
