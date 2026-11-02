# geonode-csw_services

Geonode-csw_services is a Django App to let GeoNode handle some service metadata for the exposed GeoServer services.

-----

## Configuration

1. Install the application as requirement:

       pip install -e git+https://github.com/geosolutions-it/geonode-csw-services@main#egg=csw_services

1. Add "csw_services" to your INSTALLED_APPS setting like this::

       INSTALLED_APPS = [
          'csw_services',
          ...
       ]
 
   If you have a `local_setting` file, you may want to add the `csw_services` app with these lines:
   
       INSTALLED_APPS += ('csw_services',)

1. To customize the metadata document, use your own service template:  

       CATALOG_SERVICE_METADATA_TEMPLATE = 'xml/service-template.xml'

1. Include the services in the CSW searches: GeoNode only returns the resource types listed in `PYCSW["FILTER"]`
   (by default, datasets only), so add `cswservice` to them:

       PYCSW["FILTER"] = {"resource_type__in": ["dataset", "cswservice"]}

   `GetRecordById` is not filtered, so a service record can always be fetched by its uuid.
   The services have type `service` (the ISO hierarchy level), so they can be searched with the CQL constraint
   `dc:type = 'service'`.

1. If you use the GeoNode backup/restore, add `csw_services` to both the `apps` and `dumps` lists in the
   `[fixtures]` section of its `.ini` file, after `base` and at the same position in both lists:

       [fixtures]
       apps  = ...,base,...,csw_services
       dumps = ...,base,...,csw_services

   Restore empties all the tables before loading the fixtures, so without this entry the services would
   lose their `csw_services` rows and only their bare `base` records would be restored.

## Usage

The services are created and edited in the Django admin; the `uuid` is the metadata file identifier.
For RNDT, enter it with the iPA prefix (`<iPA code>:<uuid>`), which is also what the
[rndt](https://github.com/geosolutions-it/geonode-rndt) per-PA endpoint `catalogue/csw/<iPA code>` filters on.

To regenerate the metadata documents of the services (all, or only the given ids):

    python manage.py regenerate_service_xml [-i <id> ...] [--dry-run]

## Uninstalling

To uninstall the app:

- remove the service metadata entries from the django admin
- remove the `csw_services` app from the `INSTALLED_APPS`
