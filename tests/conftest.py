import json
import os

import pytest


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def definition():
    path = os.path.join(BASE_DIR, 'task_definitions/default.json')

    with open(path, 'rb') as json_file:
        return json.load(json_file)
