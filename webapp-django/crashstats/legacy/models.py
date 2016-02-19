from django.db import models


class Router(object):

    def db_for_read(self, model, **hints):
        return {
            'legacy': 'legacy'
        }.get(model._meta.app_label)

    # at the moment
    db_for_write = db_for_read


class Product(models.Model):
    name = models.TextField(primary_key=True, db_column='product_name')
    sort = models.SmallIntegerField()
    rapid_release_version = models.TextField(blank=True, null=True)
    release_name = models.TextField()  # This field type is a guess.
    rapid_beta_version = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'products'


class ProductVersion(models.Model):
    product_version_id = models.AutoField(primary_key=True)
    product = models.ForeignKey('Product', db_column='product_name')
    # major_version = models.TextField()
    # release_version = models.TextField()  # This field type is a guess.
    version = models.TextField(db_column='version_string')
    beta_number = models.IntegerField(blank=True, null=True)
    version_sort = models.TextField()
    build_date = models.DateField()
    sunset_date = models.DateField()
    is_featured = models.BooleanField(db_column='featured_version')
    build_type = models.TextField()  # This field type is a guess.
    has_builds = models.NullBooleanField()
    is_rapid_beta = models.NullBooleanField()
    rapid_beta = models.ForeignKey('self', blank=True, null=True)
    # build_type_enum = models.TextField(blank=True, null=True)
    version_build = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'product_versions'
        unique_together = (
            ('product', 'version'),
            # ('product', 'release_version', 'beta_number'),
        )

        # api_mapping = {
        #     'product':
        # }
