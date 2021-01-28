#!/usr/bin/env python3
import os
import site

from setuptools import find_packages, setup
import sys
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

_ = """
py -3.7-32 .\setup.py build bdist_wheel --plat-name win32
py -3.8-32 .\setup.py build bdist_wheel --plat-name win32
py -3.7 .\setup.py build bdist_wheel --plat-name win-amd64
py -3.8 .\setup.py build bdist_wheel --plat-name win-amd64
twine upload dist/*

now uninstall all conflicting versions of the script:
py -3.7-32 -m pip uninstall electrumsv-sdk
py -3.8-32 -m pip uninstall electrumsv-sdk
py -3.7 -m pip uninstall electrumsv-sdk
py -3.8 -m pip uninstall electrumsv-sdk

and install the one you want:
py -3.8 -m pip install electrumsv-sdk
"""

with open('electrumsv_sdk/__init__.py', 'r') as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.strip().split('= ')[1].strip("'")
            break


def _locate_requirements():
    requirement_files = ["requirements.txt"]
    if sys.platform == 'win32':
        requirement_files.append("requirements-win32.txt")
    elif sys.platform == 'linux':
        requirement_files.append("requirements-linux.txt")


    requirements = []
    for file_name in requirement_files:
        with open(os.path.join("requirements", file_name), 'r') as f:
            requirements.extend(f.read().splitlines())
    return requirements


setup(
    name='electrumsv-sdk',
    version=version,
    install_requires=_locate_requirements(),
    description='ElectrumSV SDK',
    long_description=open('README.md', 'r').read(),
    long_description_content_type='text/markdown',
    author='Roger Taylor',
    author_email="roger.taylor.email@gmail.com",
    maintainer='Roger Taylor',
    maintainer_email='roger.taylor.email@gmail.com',
    url='https://github.com/electrumsv/electrumsv-sdk',
    download_url='https://github.com/electrumsv/electrumsv-sdk/tarball/{}'.format(version),
    license='Open BSV',
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
            'electrumsv-sdk=electrumsv_sdk.__main__:main'
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    include_package_data=True,
    package_data={"":
        [
            "electrumsv_sdk/scripts/*",
            "electrumsv-server/*",
        ],
    },
    packages=find_packages(),
)
