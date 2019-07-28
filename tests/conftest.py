import json
import os
from textwrap import dedent

import boto3
import pytest

import moto
from moto.ec2 import utils as ec2_utils
from moto.ec2 import ec2_backend

from ecs_deplojo.connection import Connection
from ecs_deplojo.task_definitions import TaskDefinition

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.yield_fixture(scope="function")
def cluster():

    with moto.mock_ecs(), moto.mock_ec2():
        boto3.setup_default_session(region_name="eu-west-1")

        ec2 = boto3.resource("ec2", region_name="eu-west-1")
        ecs = boto3.client("ecs", region_name="eu-west-1")

        known_amis = list(ec2_backend.describe_images())

        test_instance = ec2.create_instances(
            ImageId=known_amis[0].id, MinCount=1, MaxCount=1
        )[0]

        instance_id_document = json.dumps(
            ec2_utils.generate_instance_identity_document(test_instance)
        )

        cluster = ecs.create_cluster(clusterName="default")
        ecs.register_container_instance(
            cluster="default", instanceIdentityDocument=instance_id_document
        )

        yield cluster


@pytest.fixture
def connection(cluster):
    return Connection()


@pytest.fixture
def definition():
    path = os.path.join(BASE_DIR, "files/default_taskdef.json")

    with open(path, "r") as json_file:
        return TaskDefinition(json.load(json_file))


@pytest.fixture
def default_config():
    path = os.path.join(BASE_DIR, "files/default_config.yml")

    with open(path, "r") as fh:
        yield fh


@pytest.fixture
def example_project(tmpdir):
    data = """
    {
      "family": "default",
      "volumes": [],
      "containerDefinitions": [
        {
          "name": "web-1",
          "image": "${image}",
          "essential": true,
          "command": ["hello", "world"],
          "memory": 256,
          "cpu": 0,
          "portMappings": [
            {
              "containerPort": 8080,
              "hostPort": 0
            }
          ]
        },
        {
          "name": "web-2",
          "image": "${image}",
          "essential": true,
          "command": ["hello", "world"],
          "memory": 256,
          "cpu": 0,
          "portMappings": [
            {
              "containerPort": 8080,
              "hostPort": 0
            }
          ]
        }
      ]
    }
    """.strip()

    filename = tmpdir.join("task_definition.json")
    filename.write(data)

    data = dedent("""
    ---
    cluster_name: default
    environment:
      DATABASE_URL: postgresql://
    environment_groups:
      group-1:
        ENV_CODE: 12345
    task_definitions:
      web:
        template: %(template_filename)s
        environment_group: group-1
        task_role_arn: my-test
        overrides:
          web-1:
            memory: 512
            portMappings:
              - hostPort: 0
                containerPort: 8080
                protocol: tcp
    services:
      web:
        task_definition: web

    before_deploy:
      - task_definition: web
        container: web-1
        command: manage.py migrate --noinput

    after_deploy:
      - task_definition: web
        container: web-1
        command: manage.py clearsessions
    """
        % {"template_filename": filename.strpath}
    )

    filename = tmpdir.join("config.yml")
    filename.write(data)
    return filename
