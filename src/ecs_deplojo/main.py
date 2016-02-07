#!/usr/bin/env python
import copy
import sys
import json
import os.path
import re
import time
import tokenize
from string import Template

import boto3
import click
import yaml

from ecs_deplojo import utils
from ecs_deplojo.logger import logger


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
    def __init__(self):
        self.asg = boto3.client('autoscaling')
        self.ecs = boto3.client('ecs')
        self.ec2 = boto3.client('ec2')


@click.command()
@click.option('--config', required=True, type=click.File())
@click.option('--var', multiple=True, type=VarType())
@click.option('--dry-run', is_flag=True, default=False)
@click.option('--output-path', required=False, type=click.Path())
def cli(config, var, output_path, dry_run):
    base_path = os.path.dirname(config.name)
    config = yaml.load(config)
    template_vars = dict(var)

    connection = Connection()
    cluster_name = config['cluster_name']
    services = config['services']
    logger.info(
        "Starting deploy on cluster %s (%s services)",
        cluster_name, len(services))

    # Generate the task definitions
    task_definitions = generate_task_definitions(
        config, template_vars, base_path, output_path)

    # Check if all task definitions required by the services exists
    for service_name, service in services.iteritems():
        if service['task_definition'] not in task_definitions:
            logger.error(
                "Missing task definition %r for service %r",
                service['task_definition'], service_name)

    if not dry_run:

        # Register the task definitions in ECS
        register_task_definitions(connection, task_definitions)

        # Execute task def
        # XXX: Add code to wait for task
        before_deploy = config.get('before_deploy', [])
        for task in before_deploy:
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
                sys.exit(1)

        # Check if all services exist
        existing_services = utils.describe_services(
            connection.ecs, cluster=cluster_name,
            services=task_definitions.keys())
        available_services = {
            service['serviceName'] for service in existing_services
        }
        new_services = set(task_definitions.keys()) - available_services

        # Update services
        for service_name, service in services.iteritems():
            task_definition = task_definitions[service['task_definition']]
            if service_name in new_services:
                logger.info(
                    "Creating new service %s with task definition %s:%s",
                    service_name, task_definition['name'])
                connection.ecs.create_service(
                    cluster=cluster_name,
                    serviceName=service_name,
                    desiredCount=1,
                    taskDefinition=task_definition['name'])
            else:
                logger.info(
                    "Updating service %s with task defintion %s",
                    service_name, task_definition['name'])
                connection.ecs.update_service(
                    cluster=cluster_name,
                    service=service_name,
                    taskDefinition=task_definition['name'])

        logger.info("Waiting for deployments")

        # Wait till all service updates are deployed
        time.sleep(10)
        while True:
            current_services = utils.describe_services(
                connection.ecs, cluster=cluster_name,
                services=services.keys())
            time.sleep(5)
            if all(len(s['deployments']) == 1 for s in current_services):
                break


def generate_task_definitions(config, template_vars, base_path,
                              output_path=None):
    """Generate the task definitions"""
    task_definitions = {}
    for name, info in config['task_definitions'].iteritems():
        # Default environment. Always create a new dict instance since it is
        # mutated.
        env_items = {}
        env_items.update(config.get('environment', {}))

        # Environment groups
        env_group = info.get('environment_group')
        if env_group:
            env_items.update(config['environment_groups'][env_group])

        definition = generate_task_definition(
            info['template'], env_items, template_vars,
            info.get('overrides'), name=name,
            base_path=base_path)

        if output_path:
            write_task_definition(name, definition, output_path)
        task_definitions[name] = {
            'definition': definition,
        }
    return task_definitions


def register_task_definitions(connection, task_definitions):
    """Update task definitions"""

    for service_name, values in task_definitions.iteritems():
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
        container['environment'] = [
            {'name': k, 'value': str(v)}
            for k, v in container['environment'].iteritems()
        ]
    return result


def generate_task_definition(filename, environment, template_vars, overrides,
                             name, base_path=None):

    if base_path:
        filename = os.path.join(base_path, filename)

    with open(filename, 'rb') as fh:
        data = json.load(fh)

        data['family'] = name
        for container in data['containerDefinitions']:
            container['image'] = Template(container['image']).substitute(template_vars)
            container['environment'] = environment

            if overrides:
                container_overrides = overrides.get(container['name'], {})
                for key, value in container_overrides.iteritems():
                    if isinstance(container[key], list):
                        container[key].extend(value)
                    elif isinstance(container[key], dict):
                        container[key].update(value)
                    else:
                        container[key] = value

        return data


def write_task_definition(name, definition, output_path):
    filename = os.path.join(output_path, '%s.json' % name)
    with open(filename, 'wb') as fh:
        json.dump(definition, fh, indent=4)
