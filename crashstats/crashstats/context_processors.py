def current_versions(request):
    """The views are decorator such that they have 'currentversions' attached
    on the request itself.
    By returning them in this context processor we make sure they are available
    in templates like {{ currentversions }}
    """
    data = {}
    if hasattr(request, 'currentversions'):
        data['currentversions'] = request.currentversions
        product = getattr(request, 'product', None)
        version = getattr(request, 'version', None)
        releases = getattr(request, 'releases', None)
        if product:
            data['product'] = product
        if version:
            data['version'] = version
        if releases:
            data['releases'] = releases
    return data
