import json
import os

import pytest


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
