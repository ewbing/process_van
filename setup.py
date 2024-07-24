# pylint: skip-file
from setuptools import find_packages, setup

setup(
    name='VanAlloc',
    version='1.1',
    description='Process Vanguard reports into consistent rows and add classifications',
    author='Eric Bing',
    author_email='ericbing+github@gmail.com',
    url='https://github.com/ewbing/ProcessVan',
    packages=find_packages(),
    install_requires=[
        'pandas',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3.11',
    ],
)