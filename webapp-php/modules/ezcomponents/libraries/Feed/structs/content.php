<?php
/**
 * File containing the ezcFeedContentElement class.
 *
 * @package Feed
 * @version 1.2.1
 * @copyright Copyright (C) 2005-2008 eZ systems as. All rights reserved.
 * @license http://ez.no/licenses/new_bsd New BSD License
 * @filesource
 */

/**
 * Class defining a complex text element.
 *
 * @property string $src
 *                  An URL to the source of the value specified in the text property.
 *
 * @package Feed
 * @version 1.2.1
 */
class ezcFeedContentElement extends ezcFeedTextElement
{
    /**
     * The link to the source.
     *
     * @var string
     */
    public $src;
}
?>
