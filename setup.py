#!/usr/bin/env python
# coding: utf-8

import os
import sys

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

if sys.version < '3':
  import codecs
  u = lambda x: codecs.unicode_escape_decode(x)[0]
else:
  u = lambda x: x

if sys.argv[-1] == 'publish':
	os.system('python setup.py sdist upload')
	sys.exit()

setup(
    name='mongoSuite',
    version='0.2.2',
    description=u('Manage multiple instances of MongoDB on multiple hosts with one command line tool'),
    #long_description=open('README.rst').read(),
    license=open('LICENSE').read(),
    author=u('William Pain'),
    author_email=u('wpain@capensis.fr'),
    url='https://github.com/william-p/mongoSuite',
    keywords='mongo mongodb admin cluster tool cli',
    packages=['mongoSuite'],
    scripts=['scripts/mongoSuite'],
    install_requires=['paramiko', 'docopt', 'pymongo'],
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7']
)
