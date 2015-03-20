# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from configman import Namespace, RequiredConfig
from configman.converters import class_converter

from socorro.external.postgresql.dbapi2_util import execute_query_fetchall

#==============================================================================
class BugsBase(RequiredConfig):
    """Implement the /bugs service with PostgreSQL. """

    #--------------------------------------------------------------------------
    required_config = Namespace()
    # we use a crashstorage class here for the convenience of having a
    # database connection and transaction manager available.  Rather than
    # import those ourselves, using the crashstorage system allows us to
    # to exploit the same resource system that's already in use.
    required_config.add_option(
        'crashstorage_class',
        doc='the source storage class',
        default='socorro'
            '.external.postgresql.crashstorage.PostgreSQLCrashStorage',
        from_string_converter=class_converter
    )

    def __init__(self, config):
        self.config = config
        # we don't have to save the crashstorage instance itself, we're just
        # going to grab the transaction executor form it.
        crashstore = config.crashstorage_class(config)
        self.transaction = crashstore.transaction

    #--------------------------------------------------------------------------
    def _list_of_dicts(self, sql_query_results):
        bugs = []
        for row in sql_query_results:
            bug = dict(zip(("signature", "id"), row))
            bugs.append(bug)
        return bugs


#==============================================================================
class SignaturesByBugs(BugsBase):

    signatures_sql = """
    /* socorro.external.postgresql.bugs.Bugs.signatures */
        SELECT ba.signature, bugs.id
        FROM bugs
            JOIN bug_associations AS ba ON bugs.id = ba.bug_id
        WHERE bugs.id IN %s
    """    

    #--------------------------------------------------------------------------
    # this section defines the schema for the parameters in the __call__ method
    # these can be used to validate and type convert any parameters that come
    # from an outside source.
    parameter_validator_for__call__ = MethodParameterValidator()
    parameter_validator_for__call__.add_parameter(
        'bug_ids',
        required=True,
        default=[],
        doc='the ID of a crash',
    )
    
    #--------------------------------------------------------------------------
    cleaner_for__call__ = Cleaner()
    
    #--------------------------------------------------------------------------
    def __call__(self, bug_ids):
        """given a list of bug id numbers, return the associated signatures"""
        query_result = self.transaction(
            execute_query_fetchall,
            self.signatures_sql,
            (bug_ids, ),
        )
        query_result_as_list_of_dicts = self._list_of_dicts(query_result)
        return query_result_as_list_of_dicts
    
    
#==============================================================================
class Bugs(BugsBase):

    bug_ids_sql = """
    /* socorro.external.postgresql.bugs.Bugs.bug_ids */
    SELECT ba.signature, bugs.id
    FROM bugs
        JOIN bug_associations AS ba ON bugs.id = ba.bug_id
    WHERE EXISTS(
        SELECT 1 FROM bug_associations
        WHERE bug_associations.bug_id = bugs.id
        AND signature IN %s
    )
    """
    #--------------------------------------------------------------------------
    # this section defines the schema for the parameters in the __call__ method
    # these can be used to validate and type convert any parameters that come
    # from an outside source.
    parameter_validator_for__call__ = MethodParameterValidator()
    parameter_validator_for__call__.add_parameter(
        'signatures',
        required=True,
        default=[],
        doc='the ID of a crash',
    )
    
    #--------------------------------------------------------------------------
    def __call__(self, signatures):
        """given a list of signatures, return the associated bug id numbers"""
        query_result =  self.transaction(
            execute_query_fetchall,
            self.bug_ids_sql,
            (signatures, ),
        )
        query_result_as_list_of_dicts = self._list_of_dicts(query_result)
        return query_result_as_list_of_dicts



