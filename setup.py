#!/usr/bin/env python3
"""PCTWrap: PyCUTEst wrapper for Python

PCTWrap is open-source wrapper for the package PyCUTEst, that ease its use.

"""
import os
import sys
import setuptools

DOCLINES = (__doc__ or '').split("\n")
packages = setuptools.find_packages()
version = {}
with open(os.path.join(packages[0], 'version.py')) as fo:
    exec(fo.read(), version)
__version__ = version['__version__']

if sys.version_info[:2] < (3, 7):
    raise RuntimeError("Python version >= 3.7 required.")


def setup_package():
    setuptools.setup(
        name='pctwrap',
        version=__version__,
        author='Tom M. Ragonneau',
        author_email='tom.ragonneau@connect.polyu.hk',
        maintainer='Tom M. Ragonneau',
        maintainer_email='tom.ragonneau@connect.polyu.hk',
        description=DOCLINES[0],
        long_description='\n'.join(DOCLINES[2:]),
        url='https://github.com/ragonneau/PCTWrap',
        license='GNU Lesser General Public License v3 or later (LGPLv3+)',
        classifiers=[
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
            'Operating System :: MacOS',
            'Operating System :: Unix',
            'Topic :: Scientific/Engineering',
        ],
        packages=setuptools.find_packages(),
        install_requires=['scipy'],
        python_requires='>=3.7',
    )


if __name__ == '__main__':
    setup_package()
