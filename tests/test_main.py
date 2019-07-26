import copy
import os

from ecs_deplojo import main

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_register_task_definitions(cluster):
    task_definitions = {
        "service-1": {
            "definition": {
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
        }
    }
    connection = main.Connection()

    result = connection.ecs.list_task_definitions()
    assert len(result['taskDefinitionArns']) == 0

    main.register_task_definitions(connection, task_definitions)

    result = connection.ecs.list_task_definitions()
    assert len(result['taskDefinitionArns']) == 1


def test_deregister_task_definitions(cluster):
    task_definitions = {
        "service-1": {
            "definition": {
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
        }
    }

    connection = main.Connection()

    result = connection.ecs.list_task_definitions()
    assert len(result['taskDefinitionArns']) == 0

    for i in range(10):
        task_def = copy.deepcopy(task_definitions)
        main.register_task_definitions(connection, task_def)

    result = connection.ecs.list_task_definitions()
    assert len(result['taskDefinitionArns']) == 10

    main.deregister_task_definitions(connection, task_def)
    result = connection.ecs.list_task_definitions()
    assert len(result['taskDefinitionArns']) == 1
