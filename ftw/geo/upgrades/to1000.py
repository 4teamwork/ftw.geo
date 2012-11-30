from ftw.geo.setuphandlers import uninstall_products_maps
from ftw.upgrade import UpgradeStep


class UninstallProductsMaps(UpgradeStep):
    """Uninstalls Products.Maps using the quickinstaller tool.
    """

    def __call__(self):
        uninstall_products_maps(self.portal)
