import re

from setuptools import setup, find_packages


install_requires = [
    "boto3>=1.14.19,<1.15.0",
    "click==7.0",
    "pyaml==16.12.2",
    "pytz",
]

tests_requires = [
    "coverage[toml]==5.0.3",
    "flake8==3.7.8",
    "isort==5.0.6",
    "moto==1.3.14",
    "pytest==5.4.3",
    "pytest-cov==2.10.0",
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
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
)
