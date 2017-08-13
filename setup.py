import re

from setuptools import setup, find_packages


install_requires = [
    'boto3==1.4.4',
    'click==6.7',
    'pyaml==16.12.2',
]

tests_requires = [
    'flake8==3.3.0',
    'isort==4.2.5',
    'moto==0.4.31',
    'pytest==3.0.7',
    'pytest-cov==2.4.0',
    'pytest-capturelog==0.7',
]

with open('README.rst') as fh:
    long_description = re.sub(
        '^.. start-no-pypi.*^.. end-no-pypi', '', fh.read(), flags=re.M | re.S)

setup(
    name='ecs-deplojo',
    version='0.3.1',
    author='Lab Digital B.V.',
    author_email='opensource@labdigital.nl',
    url='https://www.github.com/labd/ecs-deplojo/',
    description="Deployment tool for Amazon ECS",
    long_description=long_description,
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_requires,
    extras_require={'test': tests_requires},
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    entry_points={
        'console_scripts': {
            'ecs-deplojo = ecs_deplojo.main:cli'
        }
    },
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
