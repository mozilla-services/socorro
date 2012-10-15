from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect
from django.views.decorators.http import require_POST
from django.core.urlresolvers import reverse
from django.contrib import messages

from django_browserid.base import get_audience
from django_browserid.auth import verify
from django_browserid.forms import BrowserIDForm


@require_POST
def mozilla_browserid_verify(request):
    """Custom BrowserID verifier for mozilla addresses."""
    home_url = reverse('crashstats.home',
                       args=(settings.DEFAULT_PRODUCT,))
    form = BrowserIDForm(request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        audience = get_audience(request)
        result = verify(assertion, audience)
        if not settings.ALLOWED_PERSONA_EMAILS:  # pragma: no cover
            raise ValueError(
                "No emails set up in `settings.ALLOWED_PERSONA_EMAILS`"
            )

        if result:
            if result['email'] in settings.ALLOWED_PERSONA_EMAILS:
                user = auth.authenticate(assertion=assertion,
                                         audience=audience)
                auth.login(request, user)
                messages.success(
                    request,
                    'You have successfully logged in.'
                )
            else:
                messages.error(
                    request,
                    "You logged in as %s but you don't have sufficient "
                    "privileges." % result['email']
                )
    else:
        messages.error(
            request,
            "Login failed"
        )
    return redirect(home_url)
