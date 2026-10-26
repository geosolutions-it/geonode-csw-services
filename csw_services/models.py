from enum import Enum
import errno
import logging

from geonode.resource.registry import resource_manager_registry
from guardian.shortcuts import assign_perm
from lxml import etree
from defusedxml import lxml as dlxml

from django.db import models
from django.db.models import signals
from django.conf import settings
from django.template.loader import get_template
from django.contrib.auth.models import Group

from geonode.base.models import ResourceBase
from geonode.catalogue import get_catalogue

LOGGER = logging.getLogger(__name__)


class ServiceType(Enum):
    WMS = "OGC:WMS"
    WCS = "OGC:WCS"
    WFS = "OGC:WFS"
    WMTS = "OGC:WMTS"
    OTHER = "OTHER"

    @classmethod
    def choices(cls):
        return tuple((i.name, i.value) for i in cls)


class CswService(ResourceBase):

    service_type = models.CharField(
        max_length=32,
        choices=ServiceType.choices(),
        null=False)

    class Meta(ResourceBase.Meta):
        pass

    def __init__(self, *args, **kwargs):
        super(CswService, self).__init__(*args, **kwargs)

    def get_upload_session(self):
        raise NotImplementedError()


def pre_save_service(instance, sender, **kwargs):

    instance.csw_type = 'cswservice'

    if hasattr(instance, "resource_type"):
        instance.resource_type = 'cswservice'

    # prevents filtering out from csw backend: https://github.com/GeoNode/geonode/issues/7159
    instance.alternate = 'title'

    # we don't want this resource to appear in the GUI
    instance.metadata_only = True

    if instance.abstract == '' or instance.abstract is None:
        instance.abstract = 'No abstract provided'
    if instance.title == '' or instance.title is None:
        instance.title = instance.name

    if instance.bbox_polygon is None:
        instance.set_bbox_polygon((-180, -90, 180, 90), 'EPSG:4326')
    instance.set_bounds_from_bbox(
        instance.bbox_polygon,
        instance.bbox_polygon.srid
    )


def pre_delete_service(instance, sender, **kwargs):
    resource_manager_registry.get_for_instance(instance)\
        .remove_permissions(instance.uuid, instance=instance.get_self_resource())


def post_delete_service(instance, sender, **kwargs):
    pass


def post_save_service(instance, sender, **kwargs):
    """Get information from catalogue"""
    resources = ResourceBase.objects.filter(id=instance.resourcebase_ptr.id)
    LOGGER.warning(f'*** POST SAVING SERVICE "{instance.uuid}"')
    if resources.exists():
        # Update the Catalog
        try:
            catalogue = get_catalogue()
            catalogue.create_record(instance)
            record = catalogue.get_record(instance.uuid)
        except EnvironmentError as err:
            if err.errno == errno.ECONNREFUSED:
                LOGGER.warning(f'Could not connect to catalogue to save information for layer "{instance.name}"', err)
                return
            else:
                raise err

        if not record:
            LOGGER.exception(f'Metadata record for service {instance.title} does not exist, check the catalogue signals.')
            return

        # generate an XML document
        if instance.metadata_uploaded and instance.metadata_uploaded_preserve:
            md_doc = etree.tostring(dlxml.fromstring(instance.metadata_xml))
        else:
            LOGGER.info(f'Rebuilding metadata document for "{instance.uuid}"')
            template = getattr(settings, 'CATALOG_SERVICE_METADATA_TEMPLATE', 'xml/service-template.xml')
            md_doc = create_metadata_document(instance, template)

        try:
            csw_anytext = catalogue.catalogue.csw_gen_anytext(md_doc)
        except Exception as e:
            LOGGER.exception(e)
            csw_anytext = ''

        for r in resources:
            if instance.is_published:
                anonymous_group = Group.objects.get(name='anonymous')
                assign_perm('view_resourcebase', anonymous_group, r)
            else:
                resource_manager_registry.get_for_instance(instance)\
                    .remove_permissions(instance.uuid, instance=instance.get_self_resource())


        resources.update(
            metadata_xml=md_doc,
            csw_anytext=csw_anytext)
    else:
        LOGGER.warn(f'*** The resource selected does not exists or or more than one is selected "{instance.uuid}"')


def create_metadata_document(instance, template):
    site_url = settings.SITEURL.rstrip('/') if settings.SITEURL.startswith('http') else settings.SITEURL
    tpl = get_template(template)
    ctx = {
        'service': instance,
        'SITEURL': site_url,
        'GEOSERVER_URL': settings.GEOSERVER_PUBLIC_LOCATION,
        }
    md_doc = tpl.render(context=ctx)
    return md_doc


if 'geonode.catalogue' in settings.INSTALLED_APPS:
    signals.pre_save.connect(pre_save_service, sender=CswService)
    signals.post_save.connect(post_save_service, sender=CswService)
