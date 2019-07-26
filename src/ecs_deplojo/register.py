import copy
import operator

from ecs_deplojo.logger import logger


def register_task_definitions(connection, task_definitions):
    """Update task definitions"""

    for service_name, values in task_definitions.items():
        definition = _transform_definition(values["definition"])
        result = connection.ecs.register_task_definition(**definition)

        values["family"] = result["taskDefinition"]["family"]
        values["revision"] = result["taskDefinition"]["revision"]
        values["name"] = "%s:%s" % (
            result["taskDefinition"]["family"],
            result["taskDefinition"]["revision"],
        )
        values["arn"] = result["taskDefinition"]["taskDefinitionArn"]
        logger.info("Registered new task definition %s", values["name"])


def deregister_task_definitions(connection, task_definitions):
    """Deregister all task definitions not used currently"""

    def yield_arns(family):
        paginator = connection.ecs.get_paginator("list_task_definitions")
        for page in paginator.paginate(familyPrefix=family):
            for arn in page["taskDefinitionArns"]:
                yield arn

    logger.info("Deregistering old task definitions")
    for service_name, values in task_definitions.items():
        logger.info(" - %s", values["family"])

        num = 0

        for arn in yield_arns(values["family"]):
            num += 1
            if arn != values["arn"]:
                connection.ecs.deregister_task_definition(taskDefinition=arn)

            if num > 10:
                break


def _transform_definition(definition):
    result = copy.deepcopy(definition)
    for container in result["containerDefinitions"]:
        container["environment"] = sorted(
            [{"name": k, "value": str(v)} for k, v in container["environment"].items()],
            key=operator.itemgetter("name"),
        )

    return result
