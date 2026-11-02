from django.db import migrations


def set_csw_type(csw_type):
    def update(apps, schema_editor):
        ResourceBase = apps.get_model('base', 'ResourceBase')
        ResourceBase.objects.filter(resource_type='cswservice').update(csw_type=csw_type)
    return update


class Migration(migrations.Migration):

    dependencies = [
        ('csw_services', '0002_cswservice_rename'),
    ]

    operations = [
        # the ISO hierarchy level, so that the standard dc:type = 'service' query matches the services
        migrations.RunPython(set_csw_type('service'), set_csw_type('cswservice')),
    ]
