from setuptools import setup, find_packages


install_requires = [
    'boto3>=1.0.0',
    'pyaml',
    'Click',
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
    setup_requires=['setuptools_scm'],
    use_scm_version=True,
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,
    entry_points='''
        [console_scripts]
        ecs-deplojo=ecs_deplojo.main:cli
    ''',
    license='Proprietary',
    classifiers=[
        'Private :: Do Not Upload',
        'License :: Other/Proprietary License',
    ],
)
