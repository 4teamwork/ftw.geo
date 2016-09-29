from setuptools import setup, find_packages
import os

version = '1.3.5'
maintainer = 'Lukas Graf'

tests_require = [
    'ftw.testbrowser',
    'ftw.testing',
    'mocker',
    'plone.app.testing',
    'plone.testing',
    'zope.configuration',
    'unittest2',
    'transaction',
    'plone.app.referenceablebehavior',
    'plone.directives.form',
    ]

setup(name='ftw.geo',
      version=version,
      description='Integration package for collective.geo.* packages.',
      long_description=open('README.rst').read() + '\n' + \
          open(os.path.join('docs', 'HISTORY.txt')).read(),

      classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 4.1',
        'Framework :: Plone :: 4.2',
        'Framework :: Plone :: 4.3',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Programming Language :: Python',
        'Topic :: Software Development',
        ],

      keywords='plone ftw geo',
      author='4teamwork AG',
      author_email='mailto:info@4teamwork.ch',
      maintainer=maintainer,
      url='https://github.com/4teamwork/ftw.geo',
      license='GPL2',

      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['ftw'],
      include_package_data=True,
      zip_safe=False,

      install_requires=[
        'setuptools',
        'geopy',
        'collective.geo.settings',
        'collective.geo.openlayers >= 3.0, < 4.0',
        'collective.geo.geographer',
        'collective.geo.contentlocations',
        'collective.geo.kml',
        'collective.geo.mapwidget >= 2.1, < 3.0',
        'plone.app.dexterity',
        'ftw.upgrade',
        ],

      tests_require=tests_require,
      extras_require=dict(tests=tests_require),

      entry_points='''
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      ''',
      )
