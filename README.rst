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

.. image:: https://github.com/labd/ecs-deplojo/workflows/Python%20Tests/badge.svg
    :target: https://github.com/labd/ecs-deplojo/actions?query=workflow%3A%22Python+Tests%22

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


Using SSM secrets
-----------------

When you want to use the AWS SSM secrets in your configuration you can use the `secrets`
section, however this needs some additional configuration within AWS

At first you need an AWS IAM role to use as the ECS execution role, this role needs
access to the secrets in Secrets Manager or Parameter store and will only be used during
the startup of your Docker container.

**Example configuration:**

.. code-block:: yaml

    --
    cluster_name: example

    environment:
      NORMAL_ENV_VAR: value_of_variable

    secrets:
      DATABASE_URL: /path/to/secret/DATABASE_URL

    task_definitions:
      web:
        execution_role_arn: arn:aws:iam::<account_id>:role/execution_role_name
        template: task_definitions/web.json

    services:
      web:
        task_definition: web


When the container is started the secrets are available as environment variables and
hidden in the AWS ECS console.


AWS Default VPC
---------------

When running your servers in the AWS default VPC you need ``networkMode="awsvpc"`` in
your task definition JSON file, this will ensure that no hostnames are set for the
containers, since this isn't supported by AWS.


AWS Fargate
-----------

Unlike EC2 based clusters AWS Fargate needs a ``execution_role_arn`` to work, this can be
set in your service definition in the YAML file.


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
