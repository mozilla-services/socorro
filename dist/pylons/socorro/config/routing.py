"""
Setup your Routes options here
"""
import os
from routes import Mapper

def make_map(global_conf={}, app_conf={}):
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    map = Mapper(directory=os.path.join(root_path, 'controllers'))

    # Set default route to the list of reports.  We can change this later if we
    # create a dashboard or better entry page.
    map.connect('', controller='query', action='query')
    
    # Routes to topcrasher reports.  :product and :version follow 'by....'
    # because I thought it was correct to have parameters after the controller
    # and action.
    map.connect('topcrasher/byversion/:product/:version',
                controller='topcrasher', action='byversion',
                requirements=dict(product='[a-zA-Z.]+',
                version='[0-9a-zA-Z.]+'))
    map.connect('topcrasher/bybranch/:branch', 
                controller='topcrasher', action='bybranch',
                requirements=dict(branch='[0-9a-zA-Z.]+'))

    # This route handles displaying the error page and graphics used in the 404/500
    # error pages. It should likely stay at the top to ensure that the error page is
    # displayed properly.
    map.connect('error/:action/:id', controller='error')
    
    # Define your routes. The more specific and detailed routes should be defined first,
    # so they may take precedent over the more generic routes. For more information, refer
    # to the routes manual @ http://routes.groovie.org/docs/
    map.connect('query', controller='query', action='query')
    map.connect('topcrasher', controller='topcrasher', action='index')
    map.connect(':controller/:action/:id')

    return map
