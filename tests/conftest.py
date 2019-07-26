import json
import os

import boto3
import pytest

import moto
from moto.ec2 import utils as ec2_utils
from moto.ec2 import ec2_backend

from ecs_deplojo.connection import Connection

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
        return json.load(json_file)


@pytest.fixture
def default_config():
    path = os.path.join(BASE_DIR, "files/default_config.yml")

    with open(path, "r") as fh:
        yield fh
