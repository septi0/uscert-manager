from setuptools import setup

# import uscert_manager.info without importing the package
info = {}

with open("uscert_manager/info.py") as fp:
    exec(fp.read(), info)

version = ""
with open("uscert_manager/VERSION", "r") as f:
    version = f.read().strip()

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name=info["__package_name__"],
    version=version,
    description=info["__description__"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license=info["__license__"],
    author=info["__author__"],
    author_email=info["__author_email__"],
    author_url=info["__author_url__"],
    python_requires=">=3.9",
    packages=[
        "uscert_manager",
        "uscert_manager.providers",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: System :: Archiving :: Backup",
        "Topic :: System :: Archiving :: Mirroring",
        "Topic :: Utilities",
    ],
    entry_points={
        "console_scripts": [
            "uscert-manager = uscert_manager:main",
        ],
    },
    include_package_data=True,
    package_data={
        "uscert_manager": [
            "VERSION",
        ],
    },
)
