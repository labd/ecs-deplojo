#!/usr/bin/env python
import copy
import operator
import os.path
import re
import sys
import time
import tokenize

import boto3
import click
import yaml

from ecs_deplojo import utils
from ecs_deplojo.exceptions import DeploymentFailed
from ecs_deplojo.logger import logger
from ecs_deplojo.task_definitions import generate_task_definitions

POLL_TIME = 5


class VarType(click.ParamType):
    name = 'var'
    re_pattern = re.compile('^%s$' % tokenize.Name)

    def convert(self, value, param, ctx):
        try:
            key, value = value.split('=', 1)
            if not self.re_pattern.match(key):
                self.fail('%s is not a valid identifier' % key)
        except ValueError:
            self.fail('%s is not a valid key/value string' % value, param, ctx)

        return (key, value)


class Connection(object):
    def __init__(self, role_arn):
        credentials = {}
        if role_arn:
            sts = boto3.client('sts')
            resp = sts.assume_role(
                RoleArn=role_arn,
                RoleSessionName='ecs-deplojo')
            credentials.update({
                'aws_secret_access_key': resp['Credentials']['SecretAccessKey'],
                'aws_access_key_id': resp['Credentials']['AccessKeyId'],
                'aws_session_token': resp['Credentials']['SessionToken']
            })
        self.ecs = boto3.client('ecs', **credentials)


@click.command()
@click.option('--config', required=True, type=click.File())
@click.option('--var', multiple=True, type=VarType())
@click.option('--dry-run', is_flag=True, default=False)
@click.option('--output-path', required=False, type=click.Path())
@click.option('--role-arn', required=False, type=str)
def cli(config, var, output_path, dry_run, role_arn=None):
    base_path = os.path.dirname(config.name)
    config = yaml.load(config)
    template_vars = dict(var)

    connection = Connection(role_arn)
    cluster_name = config['cluster_name']
    services = config['services']
    logger.info(
        "Starting deploy on cluster %s (%s services)",
        cluster_name, len(services))


    # Generate the task definitions
    task_definitions = generate_task_definitions(
        config, template_vars, base_path, output_path)

    # Check if all task definitions required by the services exists
    for service_name, service in services.items():
        if service['task_definition'] not in task_definitions:
            logger.error(
                "Missing task definition %r for service %r",
                service['task_definition'], service_name)

    # Run the deployment
    if not dry_run:
        try:
            start_deployment(config, connection, task_definitions)
        except DeploymentFailed:
            sys.exit(1)

    sys.exit(0)


def start_deployment(config, connection, task_definitions):
    """Start the deployment.

    The following steps are executed:

    1. The task definitions are registered with AWS
    2. The before_deploy tasks are started
    3. The services are updated to reference the last task definitions
    4. The client poll's AWS until all deployments are finished.
    5. The after_deploy tasks are started.

    """
    cluster_name = config['cluster_name']
    services = config['services']

    # Register the task definitions in ECS
    register_task_definitions(connection, task_definitions)

    # Run tasks before deploying services
    tasks_before_deploy = config.get('before_deploy', [])
    run_tasks(
        connection, cluster_name, task_definitions, tasks_before_deploy)

    # Check if all services exist
    existing_services = utils.describe_services(
        connection.ecs, cluster=cluster_name,
        services=task_definitions.keys())
    available_services = {
        service['serviceName'] for service in existing_services
    }
    new_services = set(task_definitions.keys()) - available_services

    # Update services
    for service_name, service in services.items():
        task_definition = task_definitions[service['task_definition']]
        if service_name in new_services:
            logger.info(
                "Creating new service %s with task definition %s",
                service_name, task_definition['name'])
            connection.ecs.create_service(
                cluster=cluster_name,
                serviceName=service_name,
                desiredCount=1,
                taskDefinition=task_definition['name'])
        else:
            logger.info(
                "Updating service %s with task definition %s",
                service_name, task_definition['name'])
            connection.ecs.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=task_definition['name'])

    is_finished = wait_for_deployments(
        connection, cluster_name, services.keys())

    if not is_finished:
        raise DeploymentFailed("Timeout")

    # Run tasks after deploying services
    tasks_after_deploy = config.get('after_deploy', [])
    run_tasks(
        connection, cluster_name, task_definitions, tasks_after_deploy)


def wait_for_deployments(connection, cluster_name, service_names):
    """Poll ECS until all deployments are finished (status = PRIMARY)

    """
    logger.info("Waiting for deployments")
    start_time = time.time()

    def service_description(service):
        """Return string in format of 'name (0/2)'"""
        name = service['serviceName']
        for deployment in service['deployments']:
            if deployment.get('status') != 'PRIMARY':
                continue

            desired = deployment['desiredCount']
            pending = deployment['pendingCount']
            running = deployment['runningCount']

            return '%s (%s/%s)' % (name, pending + running, desired)
        return name

    # Wait till all service updates are deployed
    time.sleep(POLL_TIME)
    while True:
        services = utils.describe_services(
            connection.ecs, cluster=cluster_name, services=service_names)

        in_progress = [s for s in services if len(s['deployments']) > 1]
        if in_progress:
            logger.info(
                "Waiting for services: %s",
                ', '.join([service_description(s) for s in in_progress]))
        else:
            logger.info(
                "Deployment finished: %s",
                ', '.join([service_description(s) for s in services]))
            break

        time.sleep(5)
        if time.time() - start_time > (60 * 15):
            logger.error("Giving up after 15 minutes")
            return False
    return True


def run_tasks(connection, cluster_name, task_definitions, tasks):
    """Run one-off tasks.


    :parameter connection: The internal connection object.
    :type connection: Connection
    :parameter cluster_name: The cluster name to run the task on
    :type cluster_name: str
    :parameter task_definitions: dict of task definitions.
    :type task_definitions: dict
    :parameter tasks: list of tasks to run.
    :type tasks: list

    """
    num = 0

    for task in tasks:
        task_def = task_definitions[task['task_definition']]
        logger.info(
            "Starting one-off task '%s' via %s (%s)",
            task['command'], task_def['name'], task['container'])

        response = connection.ecs.run_task(
            cluster=cluster_name,
            taskDefinition=task_def['name'],
            overrides={
                'containerOverrides': [
                    {
                        'name': task['container'],
                        'command': task['command'].split(),
                    }
                ]
            },
            startedBy='ecs-deplojo',
            count=1
        )
        if response.get('failures'):
            logger.error(
                "Error starting one-off task: %r", response['failures'])

            # If we already started one task then we keep retrying until
            # the previous task is finished.
            if num > 0 and num <= 30:
                time.sleep(5)
            else:
                sys.exit(1)
        num += 1


def register_task_definitions(connection, task_definitions):
    """Update task definitions"""

    for service_name, values in task_definitions.items():
        definition = transform_definition(values['definition'])
        result = connection.ecs.register_task_definition(**definition)

        values['family'] = result['taskDefinition']['family']
        values['revision'] = result['taskDefinition']['revision']
        values['name'] = '%s:%s' % (
            result['taskDefinition']['family'],
            result['taskDefinition']['revision'])
        logger.info(
            "Registered new task definition %s", values['name'])


def transform_definition(definition):
    result = copy.deepcopy(definition)
    for container in result['containerDefinitions']:
        container['environment'] = sorted([
            {'name': k, 'value': str(v)}
            for k, v in container['environment'].items()
        ], key=operator.itemgetter('name'))

    return result
