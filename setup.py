from setuptools import setup

# import uscertbot_manager.info without importing the package
info = {}

with open("uscertbot_manager/info.py") as fp:
    exec(fp.read(), info)

with open("README.md", "r") as f:
    long_description = f.read()

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f]

setup(
    name=info['__package_name__'],
    version=info['__version__'],
    description=info['__description__'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    license=info['__license__'],
    author=info['__author__'],
    author_email=info['__author_email__'],
    author_url=info['__author_url__'],
    python_requires='>=3.9',
    install_requires=requirements,
    packages=[
        'uscertbot_manager',
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
        'console_scripts': [
            'uscertbot-manager = uscertbot_manager:main',
        ],
    },
    options={}
)