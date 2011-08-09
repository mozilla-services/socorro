<?php
/**
 * File containing the ezcFeedProcessor class.
 *
 * @package Feed
 * @version 1.2.1
 * @copyright Copyright (C) 2005-2008 eZ systems as. All rights reserved.
 * @license http://ez.no/licenses/new_bsd New BSD License
 * @filesource
 */

/**
 * Base class for all feed processors.
 *
 * Currently implemented for these feed types:
 *  - RSS1 ({@link ezcFeedRss1})
 *  - RSS2 ({@link ezcFeedRss2})
 *  - ATOM ({@link ezcFeedAtom})
 *
 * Child classes must implement these methods:
 * - generate() - Returns an XML string from the feed information contained.
 *
 * @package Feed
 * @version 1.2.1
 */
abstract class ezcFeedProcessor
{
    /**
     * Holds the feed data container.
     *
     * @var ezcFeed
     * @ignore
     */
    protected $feedContainer;

    /**
     * Holds the XML document which is being generated.
     *
     * @var DOMDocument
     * @ignore
     */
    protected $xml;

    /**
     * Holds the root node of the XML document being generated.
     *
     * @var DOMNode
     * @ignore
     */
    protected $root;

    /**
     * Holds the channel element of the XML document being generated.
     *
     * @var DOMElement
     * @ignore
     */
    protected $channel;

    /**
     * Holds the prefixes used in the feed generation process.
     *
     * @var array(string)
     * @ignore
     */
    protected $usedPrefixes = array();

    /**
     * Sets the value of element $name to $value based on the feed schema.
     *
     * @param string $name The element name
     * @param mixed $value The new value for the element $name
     * @ignore
     */
    public function __set( $name, $value )
    {
        $this->feedContainer->$name = $value;
    }

    /**
     * Returns the value of element $name based on the feed schema.
     *
     * @param string $name The element name
     * @return mixed
     * @ignore
     */
    public function __get( $name )
    {
        return $this->feedContainer->$name;
    }

    /**
     * Returns if the property $name is set.
     *
     * @param string $name The property name
     * @return bool
     * @ignore
     */
    public function __isset( $name )
    {
        return isset( $this->feedContainer->$name );
    }

    /**
     * Returns an array with all the modules loaded at feed-level.
     *
     * @return array(ezcFeedModule)
     */
    public function getModules()
    {
        return $this->feedContainer->getModules();
    }

    /**
     * Creates a node in the XML document being generated with name $element
     * and value(s) $value.
     *
     * @param DOMNode $root The root in which to create the node $element
     * @param string $element The name of the XML element
     * @param mixed|array(mixed) $value The value(s) for $element
     * @ignore
     */
    protected function generateMetaData( DOMNode $root, $element, $value )
    {
        if ( !is_array( $value ) )
        {
            $value = array( $value );
        }
        foreach ( $value as $valueElement )
        {
            $meta = $this->xml->createElement( $element, ( $valueElement instanceof ezcFeedElement ) ? $valueElement->__toString() : (string)$valueElement );
            $root->appendChild( $meta );
        }
    }

    /**
     * Creates elements in the XML document being generated with name $element
     * and value(s) $value.
     *
     * @param DOMNode $root The root in which to create the node $element
     * @param string $element The name of the XML element
     * @param mixed|array(mixed) $value The value(s) for $element
     * @param array(string=>mixed) $attributes The attributes to add to the node
     * @ignore
     */
    protected function generateMetaDataWithAttributes( DOMNode $root, $element, $value = false, array $attributes )
    {
        if ( !is_array( $value ) )
        {
            $value = array( $value );
        }
        foreach ( $value as $valueElement )
        {
            if ( $valueElement === false )
            {
                $meta = $this->xml->createElement( $element );
            }
            else
            {
                $meta = $this->xml->createElement( $element, ( $valueElement instanceof ezcFeedElement ) ? $valueElement->__toString() : (string)$valueElement );
            }
            foreach ( $attributes as $attrName => $attrValue )
            {
                $attr = $this->xml->createAttribute( $attrName );
                $text = $this->xml->createTextNode( $attrValue );
                $attr->appendChild( $text );
                $meta->appendChild( $attr );
            }
            $root->appendChild( $meta );
        }
    }

    /**
     * Creates elements for all modules loaded at item-level, and adds the
     * namespaces required by the modules in the XML document being generated.
     *
     * @param ezcFeedEntryElement $item The feed item containing the modules
     * @param DOMElement $node The XML element in which to add the module elements
     * @ignore
     */
    protected function generateItemModules( ezcFeedEntryElement $item, DOMElement $node )
    {
        foreach ( $item->getModules() as $module )
        {
            $this->addAttribute( $this->root, 'xmlns:' . $module->getNamespacePrefix(), $module->getNamespace() );
            $module->generate( $this->xml, $node );
        }
    }

    /**
     * Creates elements for all modules loaded at feed-level, and adds the
     * namespaces required by the modules in the XML document being generated.
     *
     * @param DOMElement $node The XML element in which to add the module elements
     * @ignore
     */
    protected function generateFeedModules( DOMElement $node )
    {
        foreach ( $this->getModules() as $module )
        {
            $this->addAttribute( $this->root, 'xmlns:' . $module->getNamespacePrefix(), $module->getNamespace() );
            $module->generate( $this->xml, $node );
        }
    }

    /**
     * Parses the XML element $node and creates modules in the feed or
     * feed item $item.
     *
     * @param ezcFeedEntryElement|ezcFeed $item The feed or feed item which will contain the modules
     * @param DOMElement $node The XML element from which to get the module elements
     * @param string $tagName The XML tag name (if it contains ':' it will be considered part of a module)
     * @ignore
     */
    protected function parseModules( $item, DOMElement $node, $tagName )
    {
        $supportedModules = ezcFeed::getSupportedModules();
        if ( strpos( $tagName, ':' ) !== false )
        {
            list( $prefix, $key ) = explode( ':', $tagName );
            $moduleName = isset( $this->usedPrefixes[$prefix] ) ? $this->usedPrefixes[$prefix] : null;
            if ( isset( $supportedModules[$moduleName] ) )
            {
                $module = $item->hasModule( $moduleName ) ? $item->$moduleName : $item->addModule( $moduleName );
                $module->parse( $key, $node );
            }
        }
    }

    /**
     * Fetches the supported prefixes and namespaces from the XML document $xml.
     *
     * @param DOMDocument $xml The XML document object to parse
     * @return array(string=>string)
     * @ignore
     */
    protected function fetchUsedPrefixes( DOMDocument $xml )
    {
        $usedPrefixes = array();

        $xp = new DOMXpath( $xml );
        $set = $xp->query( './namespace::*', $xml->documentElement );
        $usedNamespaces = array();

        foreach ( $set as $node )
        {
            foreach ( ezcFeed::getSupportedModules() as $moduleName => $moduleClass )
            {
                $moduleNamespace = call_user_func( array( $moduleClass, 'getNamespace' ) );

                // compare the namespace URIs from the XML source with the supported ones
                if ( $moduleNamespace === $node->nodeValue )
                {
                    // the nodeName looks like: xmlns:some_module
                    list( $xmlns, $prefix ) = explode( ':', $node->nodeName );

                    // use the prefix from the XML source as a key in the array $usedPrefixes
                    // eg. array( 'some_prefix' => 'DublinCore' );
                    // then, when calling later parseModules(), if encountering an element
                    // like <some_prefix:creator>, it is checked if 'DublinCore' is supported
                    $usedPrefixes[$prefix] = $moduleName;
                }
            }
        }

        return $usedPrefixes;
    }

    /**
     * Adds an attribute to the XML node $node.
     *
     * @param DOMNode $node The node to add the attribute to
     * @param string $attribute The name of the attribute to add
     * @param mixed $value The value of the attribute
     * @ignore
     */
    protected function addAttribute( DOMNode $node, $attribute, $value )
    {
        $attr = $this->xml->createAttribute( $attribute );
        $val = $this->xml->createTextNode( $value );
        $attr->appendChild( $val );
        $node->appendChild( $attr );
    }

    /**
     * Returns a DOMNode child of $parent with name $nodeName and which has an
     * attribute $attribute with the value $value. Returns null if no such node
     * is found.
     *
     * @param DOMNode $parent The XML parent node
     * @param string $nodeName The node name to find
     * @param string $attribute The attribute of the node
     * @param mixed $value The value of the attribute
     * @return DOMNode
     * @ignore
     */
    protected function getNodeByAttribute( DOMNode $parent, $nodeName, $attribute, $value )
    {
        $result = null;
        $nodes = $parent->getElementsByTagName( $nodeName );

        foreach ( $nodes as $node )
        {
            $nodeAttribute = $node->getAttribute( $attribute );
            if ( $nodeAttribute !== null
                 && $nodeAttribute === $value )
            {
                $result = $node;
                break;
            }
        }

        return $result;
    }

    /**
     * Returns a DOMNode child of $parent with name $nodeName and which has an
     * attribute $attribute in the namespace $namespace with the value $value.
     * Returns null if no such node is found.
     *
     * @param DOMNode $parent The XML parent node
     * @param string $nodeName The node name to find
     * @param string $namespace The namespace of the attribute
     * @param string $attribute The attribute of the node
     * @param mixed $value The value of the attribute
     * @return DOMNode
     * @ignore
     */
    protected function getNodeByAttributeNS( DOMNode $parent, $nodeName, $namespace, $attribute, $value )
    {
        $result = null;
        $nodes = $parent->getElementsByTagName( $nodeName );

        foreach ( $nodes as $node )
        {
            $nodeAttribute = $node->getAttributeNS( $namespace, $attribute );
            if ( $nodeAttribute !== null
                 && $nodeAttribute === $value )
            {
                $result = $node;
                break;
            }
        }

        return $result;
    }

    /**
     * Returns an XML string from the feed information contained in this
     * processor.
     *
     * @return string
     */
    abstract public function generate();
}
?>
