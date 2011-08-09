<?php
/**
 * File containing the ezcFeedUnsupportedElementException class.
 *
 * @package Feed
 * @version 1.2.1
 * @copyright Copyright (C) 2005-2008 eZ systems as. All rights reserved.
 * @license http://ez.no/licenses/new_bsd New BSD License
 * @filesource
 */

/**
 * Thrown when an unsupported feed element is created.
 *
 * @package Feed
 * @version 1.2.1
 */
class ezcFeedUnsupportedElementException extends ezcFeedException
{
    /**
     * Constructs a new ezcFeedUnsupportedElementException.
     *
     * @param string $name The element name
     */
    public function __construct( $name )
    {
        parent::__construct( "The feed element '{$name}' is not supported." );
    }
}
?>
