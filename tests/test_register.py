import copy
import os

from ecs_deplojo import register
from ecs_deplojo.task_definitions import TaskDefinition

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_transform_definition(definition):
    definition.container_definitions[0]["environment"] = {
        "DEBUG": True,
        "AWS_REGION": "eu-west-1",
    }
    result = definition.as_dict()

    assert result["containerDefinitions"][0]["environment"] == [
        {"name": "AWS_REGION", "value": "eu-west-1"},
        {"name": "DEBUG", "value": "True"},
    ]


def test_register_task_definitions(cluster, connection):
    task_definitions = {
        "service-1": TaskDefinition(
            {
                "family": "my-task-def",
                "volumes": [],
                "containerDefinitions": [
                    {
                        "name": "default",
                        "image": "my-docker-image:1.0",
                        "essential": True,
                        "command": ["hello", "world"],
                        "hostname": "my-task-def",
                        "memory": 256,
                        "cpu": 0,
                        "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                        "environment": {},
                    }
                ],
                "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
            }
        )
    }

    result = connection.ecs.list_task_definitions()
    assert len(result["taskDefinitionArns"]) == 0

    register.register_task_definitions(connection, task_definitions)

    result = connection.ecs.list_task_definitions()
    assert len(result["taskDefinitionArns"]) == 1


def test_deregister_task_definitions(cluster, connection):
    task_definitions = {
        "service-1": TaskDefinition(
            {
                "family": "my-task-def",
                "volumes": [],
                "containerDefinitions": [
                    {
                        "name": "default",
                        "image": "my-docker-image:1.0",
                        "essential": True,
                        "command": ["hello", "world"],
                        "hostname": "my-task-def",
                        "memory": 256,
                        "cpu": 0,
                        "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                        "environment": {},
                    }
                ],
                "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
            }
        )
    }

    result = connection.ecs.list_task_definitions()
    assert len(result["taskDefinitionArns"]) == 0

    for i in range(10):
        task_def = copy.deepcopy(task_definitions)
        register.register_task_definitions(connection, task_def)

    result = connection.ecs.list_task_definitions()
    assert len(result["taskDefinitionArns"]) == 10

    register.deregister_task_definitions(connection, task_def)
    result = connection.ecs.list_task_definitions()
    assert len(result["taskDefinitionArns"]) >= 1
