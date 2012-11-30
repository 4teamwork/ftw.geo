from Products.CMFCore.utils import getToolByName
import logging


log = logging.getLogger('ftw.geo')


def uninstall_products_maps(context):
    """Uninstalls Products.Maps using the quickinstaller tool.
    """
    quickinstaller = getToolByName(context, 'portal_quickinstaller')
    if quickinstaller.isProductInstalled('Maps'):
        log.info('Uninstalling Products.Maps...')
        quickinstaller.uninstallProducts(['Maps'])
        log.info('Successfully uninstalled Products.Maps.')


def import_various(context):
    """Import step for configuration that is not handled in xml files.
    """
    # Only run step if a flag file is present
    if context.readDataFile('ftw.geo_default.txt') is None:
        return
    site = context.getSite()
    uninstall_products_maps(site)
