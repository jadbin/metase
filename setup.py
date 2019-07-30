# coding=utf-8

import re
import sys
from os.path import join, dirname
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

with open(join(dirname(__file__), 'README.rst'), 'r', encoding='utf-8') as fd:
    long_description = fd.read()


def read_version():
    p = join(dirname(__file__), 'metase', '__init__.py')
    with open(p, 'r', encoding='utf-8') as f:
        return re.search(r"__version__ = '([^']+)'", f.read()).group(1)


class PyTest(TestCommand):
    def run_tests(self):
        import pytest

        errno = pytest.main(['tests'])
        sys.exit(errno)


install_requires = [
    'tornado>=6.0.3',
    'xpaw>=0.11.1'
]

with open(join(dirname(__file__), 'requirements/test.txt'), 'r', encoding='utf-8') as f:
    tests_require = [l.strip() for l in f]


def main():
    if sys.version_info < (3, 5, 3):
        raise RuntimeError("The minimal supported Python version is 3.5.3")

    setup(
        name="metase",
        version=read_version(),
        url="https://github.com/jadbin/metase",
        description="Meta Search Engine",
        long_description=long_description,
        author="jadbin",
        author_email="jadbin.com@hotmail.com",
        license="Apache 2",
        zip_safe=False,
        packages=find_packages(exclude=("tests",)),
        include_package_data=True,
        entry_points={
            "console_scripts": ["metase = metase.cmdline:main"]
        },
        python_requires='>=3.5.3',
        install_requires=install_requires,
        tests_require=tests_require,
        cmdclass={"test": PyTest},
        classifiers=[
            "License :: OSI Approved :: Apache Software License",
            "Intended Audience :: Developers",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Topic :: Internet :: WWW/HTTP",
            "Topic :: Software Development :: Libraries :: Application Frameworks"
        ]
    )


if __name__ == "__main__":
    main()
