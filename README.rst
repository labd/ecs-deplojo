ecs-deplojo
===========

Deployment tool for Amazon ECS.

Installation
------------

`pip install ecs-deplojo`

.. start-no-pypi

Status
------

.. image:: https://readthedocs.org/projects/ecs-deplojo/badge/?version=latest
    :target: https://readthedocs.org/projects/ecs-deplojo/
   
.. image:: https://travis-ci.org/LabD/ecs-deplojo.svg?branch=master
    :target: https://travis-ci.org/LabD/ecs-deplojo

.. image:: http://codecov.io/github/LabD/ecs-deplojo/coverage.svg?branch=master 
    :target: http://codecov.io/github/LabD/ecs-deplojo?branch=master

.. image:: https://img.shields.io/pypi/v/ecs-deplojo.svg
    :target: https://pypi.python.org/pypi/ecs-deplojo/

.. end-no-pypi


Usage
-----

.. code-block:: console

    Usage: ecs-deplojo [OPTIONS]

    Options:
      --config FILENAME   [required]
      --var VAR
      --dry-run
      --output-path PATH
      --role-arn <optional arn>
      --help              Show this message and exit.


Example configuration
---------------------

.. code-block:: yaml

    ---
    cluster_name: example

    environment:
        DATABASE_URL: postgresql://

    task_definitions:
      web: 
        template: task_definitions/web.json
        overrides:
          uwsgi:
            memory: 512
            portMappings:
              - hostPort: 0
                containerPort: 8080
                protocol: tcp
      manage:
        template: task_definitions/manage.json

    services:
      web: 
        task_definition: web

    before_deploy:
      - task_definition: manage
        container: uwsgi
        command: manage.py migrate --noinput

    after_deploy:
      - task_definition: manage
        container: uwsgi
        command: manage.py clearsessions


Example log output
------------------

.. code-block:: console

    Starting deploy on cluster example (1 services)
    Registered new task definition web:10
    Starting one-off task 'manage.py migrate --noinput' via manage:10 (uwsgi)
    Updating service web with task defintion web:10
    Waiting for deployments
    Waiting for services: web (0/2)
    Waiting for services: web (1/2)
    Waiting for services: web (2/2)
    Deployment finished: web (2/2)
    Starting one-off task 'manage.py clearsessions' via manage:10 (uwsgi)
