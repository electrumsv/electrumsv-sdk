#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

from setuptools import find_packages, setup

__version__ = '0.0.1'

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(Path("electrumsv_sdk").joinpath("config.json").__str__(), 'r') as f:
    config = json.loads(f.read())

if sys.version_info[:3] < (3, 7, 0):
    sys.exit("Error: ElectrumSV requires Python version >= 3.7.0...")

if sys.platform == 'win32':
    with open('electrumsv_sdk/requirements/requirements-win32.txt', 'r') as f:
        requirements = f.read().splitlines()

elif sys.platform == 'linux':
    with open('electrumsv_sdk/requirements/requirements-linux.txt', 'r') as f:
        requirements = f.read().splitlines()

setup(
    name='electrumsv-sdk',
    version=__version__,
    requirements=requirements,
    description='ElectrumSV SDK',
    long_description=open('README.rst', 'r').read(),
    long_description_content_type='text/markdown',
    author='Roger Taylor',
    author_email="roger.taylor.email@gmail.com",
    maintainer='Roger Taylor',
    maintainer_email='roger.taylor.email@gmail.com',
    url='https://github.com/electrumsv/electrumsv-sdk',
    download_url='https://github.com/electrumsv/electrumsv-sdk/tarball/{}'.format(__version__),
    license='MIT',
    keywords=[
        'bitcoinsv',
        'bsv',
        'bitcoin sv',
        'cryptocurrency',
        'tools',
        'wallet',
    ],
    entry_points={
        'console_scripts': [
            'electrumsv-sdk=electrumsv_sdk.app:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    include_package_data=True,
    packages=find_packages(),
)
