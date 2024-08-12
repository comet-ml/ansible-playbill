# setup.py
import subprocess
from setuptools import setup


def get_version():
    # Run your bash script and capture the output
    version = subprocess.check_output([
        './.version/calculate-version.sh'
    ]).strip().decode('utf-8')
    return version


setup(
    version=get_version(),  # Dynamically set the version
)
