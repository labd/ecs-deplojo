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
]


setup(
    name='ecs-deplojo',
    version='0.0.1',
    author='Lab Digital B.V.',
    author_email='info@labdigital.nl',
    url='https://www.github.com/labd/ecs-deplojo/',
    description="Deployment tool for Amazon ECS",
    zip_safe=False,
    install_requires=install_requires,
    tests_require=tests_requires,
    extras_require={'test': tests_requires},
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    entry_points={
        'console_scripts': {
            'ecs-deplojo = ecs_deplojo.main:cli'
        }
    },
    license='Proprietary',
    classifiers=[
        'Private :: Do Not Upload',
        'License :: Other/Proprietary License',
    ],
)
