import os.path
import re
import sys
import tokenize

import click
import yaml

from ecs_deplojo.connection import Connection
from ecs_deplojo.deployment import DeploymentFailed, start_deployment
from ecs_deplojo.logger import logger
from ecs_deplojo.task_definitions import generate_task_definitions


class VarType(click.ParamType):
    name = "var"
    re_pattern = re.compile("^%s$" % tokenize.Name)

    def convert(self, value, param, ctx):
        try:
            key, value = value.split("=", 1)
            if not self.re_pattern.match(key):
                self.fail("%s is not a valid identifier" % key)
        except ValueError:
            self.fail("%s is not a valid key/value string" % value, param, ctx)

        return (key, value)


@click.command()
@click.option("--config", required=True, type=click.File())
@click.option("--var", multiple=True, type=VarType())
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--output-path", required=False, type=click.Path())
@click.option("--role-arn", required=False, type=str)
def main(config, var, output_path, dry_run, role_arn=None):
    base_path = os.path.dirname(config.name)
    config = yaml.safe_load(config)
    template_vars = dict(var)

    connection = Connection(role_arn)
    cluster_name = config["cluster_name"]
    services = config["services"]
    logger.info(
        "Starting deploy on cluster %s (%s services)", cluster_name, len(services)
    )

    # Generate the task definitions
    task_definitions = generate_task_definitions(
        config, template_vars, base_path, output_path
    )

    # Check if all task definitions required by the services exists
    for service_name, service in services.items():
        if service["task_definition"] not in task_definitions:
            logger.error(
                "Missing task definition %r for service %r",
                service["task_definition"],
                service_name,
            )

    # Run the deployment
    if not dry_run:
        try:
            start_deployment(config, connection, task_definitions)
        except DeploymentFailed:
            sys.exit(1)

    sys.exit(0)
