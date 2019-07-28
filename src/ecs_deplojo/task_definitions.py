import copy
import json
import operator
import os.path
import typing
from string import Template


class TaskDefinition:
    """A TaskDefinition exists out of a set of containers."""

    def __init__(self, data):
        self._data = data

    @classmethod
    def load(cls, fh) -> "TaskDefinition":
        data = json.load(fh)
        return cls(data)

    def as_dict(self):
        """Output the TaskDefinition in a boto3 compatible format.

        See the boto3 documentation on `ECS.Client.register_task_definition`.
        """
        result = copy.deepcopy(self._data)
        for container in result["containerDefinitions"]:
            container["environment"] = sorted(
                [
                    {"name": k, "value": str(v)}
                    for k, v in container.get("environment", {}).items()
                ],
                key=operator.itemgetter("name"),
            )
        return result

    def apply_variables(self, variables: typing.Dict[str, str]):
        """Interpolate all the variables used in the task definition"""
        for container in self.container_definitions:
            container["image"] = Template(container["image"]).substitute(variables)

    def apply_overrides(self, overrides):
        """Apply overrides for all containers within this task definition."""
        for container in self.container_definitions:
            container_overrides = overrides.get(container["name"], {})
            for key, value in container_overrides.items():
                if key in container and isinstance(container[key], list):
                    container[key].extend(value)
                elif key in container and isinstance(container[key], dict):
                    container[key].update(value)
                else:
                    container[key] = value

    def set_environment(self, env: typing.Dict[str, str]):
        """Interpolate all the variables used in the task definition"""
        for container in self.container_definitions:
            container["environment"] = env

    def __str__(self):
        if self._data.get("name"):
            return self._data.get("name")
        return "(unregistered)"

    def __eq__(self, other: object):
        if not isinstance(other, TaskDefinition):
            return False
        return self._data == other._data

    def __repr__(self):
        return json.dumps(self._data)

    @property
    def tags(self) -> typing.List[typing.Dict[str, str]]:
        return self._data.get("tags")

    @tags.setter
    def tags(self, value: typing.List[typing.Dict[str, str]]):
        self._data["tags"] = value

    @property
    def family(self) -> str:
        return self._data.get("family")

    @family.setter
    def family(self, value: str):
        self._data["family"] = value

    @property
    def revision(self) -> int:
        return self._data.get("revision")

    @revision.setter
    def revision(self, value: int):
        self._data["revision"] = value

    @property
    def name(self) -> str:
        return self._data.get("name")

    @name.setter
    def name(self, value: str):
        self._data["name"] = value

    @property
    def task_role_arn(self) -> str:
        return self._data.get("taskRoleArn")

    @task_role_arn.setter
    def task_role_arn(self, value: str):
        self._data["taskRoleArn"] = value

    @property
    def arn(self) -> str:
        return self._data.get("arn")

    @arn.setter
    def arn(self, value: str):
        self._data["arn"] = value

    @property
    def container_definitions(self):
        return self._data.get("containerDefinitions")

    @container_definitions.setter
    def container_definitions(self, value):
        self._data["containerDefinitions"] = value


def generate_task_definitions(
    config, template_vars, base_path, output_path=None
) -> typing.Dict[str, TaskDefinition]:
    """Generate the task definitions

    :parameter config: The yaml config contents
    :parameter template_vars: Key-Value dict with template replacements
    :parameter base_path: The base path (location of the config file)
    :parameter output_path: Optional path to write the task definitions to.
    :rtype dict:

    """
    task_definitions = {}

    for name, info in config["task_definitions"].items():
        # Create a copy of the environment dict so that it can safely be
        # modified.
        env_vars = copy.deepcopy(config.get("environment", {}))

        # Environment groups
        env_group = info.get("environment_group")
        if env_group:
            env_vars.update(config["environment_groups"][env_group])

        overrides = info.get("overrides", {})
        definition = generate_task_definition(
            filename=info["template"],
            environment=env_vars,
            template_vars=template_vars,
            overrides=overrides,
            name=name,
            base_path=base_path,
            task_role_arn=info.get("task_role_arn"),
        )

        if output_path:
            write_task_definition(name, definition, output_path)
        task_definitions[name] = definition
    return task_definitions


def generate_task_definition(
    filename: str,
    environment: typing.Dict[str, str],
    template_vars,
    overrides,
    name,
    base_path=None,
    task_role_arn=None,
) -> TaskDefinition:

    """Generate the task definitions"""
    if base_path:
        filename = os.path.join(base_path, filename)

    with open(filename, "r") as fh:
        task_definition = TaskDefinition.load(fh)

    task_definition.family = name
    if task_role_arn:
        task_definition.task_role_arn = task_role_arn

    # If no hostname is specified for the container we set it ourselves to
    # `{family}-{container-name}-{num}`
    num_containers = len(task_definition.container_definitions)
    for container in task_definition.container_definitions:
        hostname = task_definition.family
        if num_containers > 1:
            hostname += "-%s" % container["name"].replace("_", "-")
        container.setdefault("hostname", hostname)

    task_definition.set_environment(environment)
    task_definition.apply_variables(template_vars)
    task_definition.apply_overrides(overrides)
    task_definition.tags = [{"key": "createdBy", "value": "ecs-deplojo"}]

    return task_definition


def write_task_definition(name: str, definition: TaskDefinition, output_path) -> None:
    filename = os.path.join(output_path, "%s.json" % name)
    with open(filename, "w") as fh:
        json.dump(definition.as_dict(), fh, indent=4)
