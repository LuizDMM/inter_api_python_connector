import codecs
import os
import re

from setuptools import find_packages, setup

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r") as f:
    long_description = f.read()


def read(*parts):
    with codecs.open(os.path.join(BASE_DIR, *parts), "r") as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="inter_api_connector",
    version=find_version("src", "inter_api_connector", "__init__.py"),
    description="Um conector não oficial para API do Banco Inter.",
    package_dir={"": "src"},
    packages=find_packages("src"),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LuizDMM/api-inter-python-connector",
    project_urls={
        "Source": "https://github.com/LuizDMM/api-inter-python-connector",
    },
    author="LuizDMM",
    author_email="luizdmmainart@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: Portuguese (Brazilian)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Topic :: Office/Business :: Financial",
    ],
    install_requires=[
        "requests>=2.31.0",
        "pyOpenSSL>=23.3.0",
        "cryptography>=1.3.4",
        "idna>=2.0",
    ],
    extras_require={
        "dev": ["build>=1.0.3", "sphinx"],
    },
    python_requires=">=3.8",
)
