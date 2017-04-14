import json
import os

import boto3
import pytest
import moto


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.yield_fixture(scope="function")
def connection():
    boto3.setup_default_session(region_name='eu-west-1')

    moto.mock_autoscaling().start()
    moto.mock_ecs().start()
    moto.mock_ec2().start()

    from ecs_deplojo import main

    yield main.Connection()

    moto.mock_autoscaling().stop()
    moto.mock_ecs().stop()
    moto.mock_ec2().stop()


@pytest.fixture
def definition():
    path = os.path.join(BASE_DIR, 'files/default_taskdef.json')

    with open(path, 'rb') as json_file:
        return json.load(json_file)


@pytest.fixture
def default_config():
    path = os.path.join(BASE_DIR, 'files/default_config.yml')

    with open(path, 'rb') as fh:
        yield fh
