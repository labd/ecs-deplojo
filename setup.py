import re

from setuptools import setup, find_packages


install_requires = [
    "boto3>=1.36.2",
    "click==8.1.8",
    "pyaml==25.1.0",
    "pytz",
]

tests_requires = [
    "coverage[toml]==7.6.10",
    "flake8",
    "isort",
    "moto",
    "pytest==8.3.4",
    "pytest-cov==6.0.0",
]

with open("README.rst") as fh:
    long_description = re.sub(
        "^.. start-no-pypi.*^.. end-no-pypi", "", fh.read(), flags=re.M | re.S
    )

setup(
    name="ecs-deplojo",
    version="0.9.2",
    author="Lab Digital B.V.",
    author_email="opensource@labdigital.nl",
    url="https://www.github.com/labd/ecs-deplojo/",
    description="Deployment tool for Amazon ECS",
    long_description=long_description,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_requires,
    extras_require={"test": tests_requires},
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    entry_points={"console_scripts": {"ecs-deplojo = ecs_deplojo.cli:main"}},
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
