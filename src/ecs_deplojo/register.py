import typing

from ecs_deplojo.connection import Connection
from ecs_deplojo.logger import logger
from ecs_deplojo.task_definitions import TaskDefinition


def register_task_definitions(
    connection: Connection, task_definitions: typing.Dict[str, TaskDefinition]
) -> None:
    """Update task definitions"""

    for service_name, task_definition in task_definitions.items():
        definition = task_definition.as_dict()
        result = connection.ecs.register_task_definition(**definition)

        task_definition.family = result["taskDefinition"]["family"]
        task_definition.revision = result["taskDefinition"]["revision"]
        task_definition.name = "%s:%s" % (
            result["taskDefinition"]["family"],
            result["taskDefinition"]["revision"],
        )
        task_definition.arn = result["taskDefinition"]["taskDefinitionArn"]
        logger.info("Registered new task definition %s", task_definition)


def deregister_task_definitions(
    connection: Connection, task_definitions: typing.Dict[str, TaskDefinition]
) -> None:
    """Deregister all task definitions not used currently which are created
    by ecs-deplojo.

    """
    def yield_arns(family) -> typing.Generator[str, None, None]:
        paginator = connection.ecs.get_paginator("list_task_definitions")
        for page in paginator.paginate(familyPrefix=family):
            for arn in page['taskDefinitionArns']:
                info = connection.ecs.list_tags_for_resource(resourceArn=arn)
                tags = {i['key']: i['value'] for i in info['tags']}
                if tags.get('createdBy') == 'ecs-deplojo':
                    yield arn

    logger.info("Deregistering old task definitions")
    for service_name, task_definition in task_definitions.items():
        logger.info(" - %s", task_definition.family)

        num = 0

        for arn in yield_arns(task_definition.family):
            num += 1
            if arn != task_definition.arn:
                connection.ecs.deregister_task_definition(taskDefinition=arn)

            if num > 10:
                break
