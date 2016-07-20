from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


def migrate_users(combos, dry_run=False):
    # Because the list of comboes is possibly very large, we don't want
    # to query the ORM for each and every one since most of the emails
    # we expect to search for are not going to be found.
    size = 100
    groups = [
        combos[i:i + size] for i in range(0, len(combos), size)
    ]
    for group in groups:
        transform = dict((x.lower(), y) for x, y in group)

        q = Q()
        for email in transform:
            q = q | Q(email__iexact=email)
        # Most likely the list of emails we search for is MUCH larger
        # than the number of users we find. For those few found,
        # we'll deal with it one at a time.
        users = User.objects.filter(q)
        for user in users:
            print 'NEED TO MIGRATE', user.email.ljust(30),
            print 'TO', transform[user.email.lower()]
            try:
                destination = User.objects.get(
                    email__iexact=transform[user.email.lower()]
                )
                if user.is_staff:
                    print "\tTransferring 'is_staff'"
                    destination.is_staff = True
                if user.is_superuser:
                    print "\tTransferring 'is_superuser'"
                    destination.is_superuser = True
                for group in user.groups.all():
                    print '\tTransferring group membership %r' % group.name
                    destination.groups.add(group)
                if (
                    user.last_login and destination.last_login and
                    user.last_login > destination.last_login
                ):
                    destination.last_login = user.last_login
                if (
                    user.date_joined and destination.date_joined and
                    user.date_joined > destination.date_joined
                ):
                    destination.date_joined = user.date_joined
                user.is_active = False
                if not dry_run:
                    user.save()
                    destination.save()
            except User.DoesNotExist:
                # then it's easy peasy!
                print '\tSimply changing email from %r to %r' % (
                    user.email,
                    transform[user.email.lower()]
                )
                user.email = transform[user.email.lower()]
                if not dry_run:
                    user.save()
