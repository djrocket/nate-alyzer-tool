# setup.py
from setuptools import find_packages, setup

setup(
    name="nate_alyzer_agent",
    version="0.1.0",
    package_dir={"": "nate_alyzer_agent"}, # <-- ADD THIS LINE
    packages=find_packages(where="nate_alyzer_agent"), # <-- MODIFY THIS LINE
)