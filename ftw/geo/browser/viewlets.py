from collective.geo.kml.browser.viewlets import ContentViewlet


class FtwGeoContentMapViewlet(ContentViewlet):
    """Content map viewlet to be used anywhere, not just in the viewlet
    managers defined in collective.geo.settings.
    """

    def render(self):
        coords = self.coordinates
        if coords.type and coords.coordinates:
            # Don't call the render method of the c.geo.kml viewlet but
            # the one from its superclass to avoid the condition that only
            # renders the viewlet if it's in one of the predefined managers
            return super(ContentViewlet, self).render()
        else:
            return ''
