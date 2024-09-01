# setup.py
import subprocess
from setuptools import setup
import os


def get_version():
    # Run your bash script and capture the output
    version = subprocess.check_output([
        './.version/calculate-version.sh'
    ]).strip().decode('utf-8')
    return version


setup(
    version=os.environ.get('VERSION', get_version()), # Dynamically set the version
    long_description=open('README.md',encoding="utf-8").read(),
    long_description_content_type='text/markdown',
)
