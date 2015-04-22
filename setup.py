# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup

version = '0.1'

setup(name='phanalyzer',
      version=version,
      description="Automated regression detection for performance data",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='William Lachance',
      author_email='wrlach@gmail.com',
      url='https://github.com/wlach/phanalyzer',
      license='MPL',
      packages=['phanalyzer'],
      zip_safe=False,
      install_requires=[]
      )
