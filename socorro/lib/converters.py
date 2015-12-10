import ujson

from configman import RequiredConfig, Namespace, class_converter


#------------------------------------------------------------------------------
def _default_list_splitter(class_list_str):
    return [x.strip() for x in class_list_str.split(',') if x.strip()]


#------------------------------------------------------------------------------
def _default_class_extractor(list_element):
    return list_element


#------------------------------------------------------------------------------
def str_to_classes_in_namespaces_converter(
        template_for_namespace="%(name)s",
        list_splitter_fn=_default_list_splitter,
        class_extractor=_default_class_extractor,
        name_of_class_option='qualified_class_name',
        instantiate_classes=False,
):
    """
    parameters:
        template_for_namespace - a template for the names of the namespaces
                                 that will contain the classes and their
                                 associated required config options.  There are
                                 two template variables available: %(name)s -
                                 the name of the class to be contained in the
                                 namespace; %(index)d - the sequential index
                                 number of the namespace.
        list_converter - a function that will take the string list of classes
                         and break it up into a sequence if individual elements
        class_extractor - a function that will return the string version of
                          a classname from the result of the list_converter
    """

    # -------------------------------------------------------------------------
    def class_list_converter(class_list_str):
        """This function becomes the actual converter used by configman to
        take a string and convert it into the nested sequence of Namespaces,
        one for each class in the list.  It does this by creating a proxy
        class stuffed with its own 'required_config' that's dynamically
        generated."""
        if isinstance(class_list_str, basestring):
            class_str_list = list_splitter_fn(class_list_str)
        else:
            raise TypeError('must be derivative of a basestring')

        # =====================================================================
        class InnerClassList(RequiredConfig):
            """This nested class is a proxy list for the classes.  It collects
            all the config requirements for the listed classes and places them
            each into their own Namespace.
            """
            # we're dynamically creating a class here.  The following block of
            # code is actually adding class level attributes to this new class

            # 1st requirement for configman
            required_config = Namespace()

            # to help the programmer know what Namespaces we added
            subordinate_namespace_names = []

            # save the template for future reference
            namespace_template = template_for_namespace

            # for display
            original_input = class_list_str.replace('\n', '\\n')

            # for each class in the class list
            class_list = []
            for namespace_index, class_list_element in enumerate(
                class_str_list
            ):
                a_class = class_converter(
                    class_extractor(class_list_element)
                )

                # figure out the Namespace name
                namespace_name_dict = {
                    'name': a_class.__name__,
                    'index': namespace_index
                }
                namespace_name = template_for_namespace % namespace_name_dict
                class_list.append((a_class.__name__, a_class, namespace_name))
                subordinate_namespace_names.append(namespace_name)
                # create the new Namespace
                required_config.namespace(namespace_name)
                a_class_namespace = required_config[namespace_name]
                a_class_namespace.add_option(
                    name_of_class_option,
                    doc='fully qualified classname',
                    default=class_list_element,
                    from_string_converter=class_converter,
                    likely_to_be_changed=True,
                )

            @classmethod
            def to_str(cls):
                """this method takes this inner class object and turns it back
                into the original string of classnames.  This is used
                primarily as for the output of the 'help' option"""
                return "'%s'" % cls.original_input

        return InnerClassList  # result of class_list_converter

    return class_list_converter  # result of classes_in_namespaces_converter


#------------------------------------------------------------------------------
def web_services_from_str(
    list_splitter_fn=ujson.loads,
):
    """
    parameters:
        list_splitter_fn - a function that will take the json compatible string
            rerpesenting a list of mappings.
    """

    # -------------------------------------------------------------------------
    def class_list_converter(collector_services_str):
        """This function becomes the actual converter used by configman to
        take a string and convert it into the nested sequence of Namespaces,
        one for each class in the list.  It does this by creating a proxy
        class stuffed with its own 'required_config' that's dynamically
        generated."""
        if isinstance(collector_services_str, basestring):
            all_collector_services = list_splitter_fn(collector_services_str)
        else:
            raise TypeError('must be derivative of a basestring')

        # =====================================================================
        class InnerClassList(RequiredConfig):
            """This nested class is a proxy list for the classes.  It collects
            all the config requirements for the listed classes and places them
            each into their own Namespace.
            """
            # we're dynamically creating a class here.  The following block of
            # code is actually adding class level attributes to this new class

            # 1st requirement for configman
            required_config = Namespace()

            # to help the programmer know what Namespaces we added
            subordinate_namespace_names = []

            # for display
            original_input = collector_services_str.replace('\n', '\\n')

            # for each class in the class list
            service_list = []
            for namespace_index, collector_service_element in enumerate(
                all_collector_services
            ):
                service_name = collector_service_element['name']
                service_uri = collector_service_element['uri']
                service_implementation_class = class_converter(
                    collector_service_element['service_implementation_class']
                )

                service_list.append(
                    (
                        service_name,
                        service_uri,
                        service_implementation_class,
                    )
                )
                subordinate_namespace_names.append(service_name)
                # create the new Namespace
                required_config.namespace(service_name)
                a_class_namespace = required_config[service_name]
                a_class_namespace.add_option(
                    "service_implementation_class",
                    doc='fully qualified classname for a class that implements'
                        'the action associtated with the URI',
                    default=service_implementation_class,
                    from_string_converter=class_converter,
                    likely_to_be_changed=True,
                )
                a_class_namespace.add_option(
                    "uri",
                    doc='uri for this service',
                    default=service_uri,
                    likely_to_be_changed=True,
                )

            @classmethod
            def to_str(cls):
                """this method takes this inner class object and turns it back
                into the original string of classnames.  This is used
                primarily as for the output of the 'help' option"""
                return "'%s'" % cls.original_input

        return InnerClassList  # result of class_list_converter

    return class_list_converter  # result of classes_in_namespaces_converter


#------------------------------------------------------------------------------
def change_default(
    kls,
    key,
    new_default,
    new_converter=None,
    new_reference_value=None,
):
    """return a new configman Option object that is a copy of an existing one,
    giving the new one a different default value"""
    an_option = kls.get_required_config()[key].copy()
    an_option.default = new_default
    if new_converter:
        an_option.from_string_converter = new_converter
    if new_reference_value:
        an_option.reference_value_from = new_reference_value
    return an_option

