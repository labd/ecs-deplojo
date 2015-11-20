#!/usr/bin/env python
import contextlib
import copy
import itertools
import json
import logging
import operator
import os.path
import re
import time
import tokenize
from string import Template

import boto3
import click
import yaml

from ecs_deplojo import utils
from ecs_deplojo.utils import lock_deployment
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
    asg_name = config['auto_scaling_group']
    cluster_name = config['cluster_name']
    logger.info("Starting deploy on cluster %s", cluster_name)

    # Generate the task definitions
    task_definitions = {}
    for service_name, service_config in config['services'].iteritems():
        # Default environment
        env_items = config.get('environment', {})

        # Environment groups
        env_group = service_config.get('environment_group')
        if env_group:
            env_items.update(config['environment_groups'][env_group])

        definition = generate_task_definition(
            service_config['task_definition'], env_items, template_vars,
            service_config.get('overrides'), name=service_name,
            base_path=base_path)

        if output_path:
            write_task_definition(service_name, definition, output_path)
        task_definitions[service_name] = {
            'definition': definition,
        }

    # Register the task definitions in ECS
    if not dry_run:

        # Update task definitions
        for service_name, values in task_definitions.iteritems():
            definition = transform_definition(values['definition'])
            result = connection.ecs.register_task_definition(**definition)

            values['family'] = result['taskDefinition']['family']
            values['revision'] = result['taskDefinition']['revision']

            logger.info(
                "Registered new task definition %s:%s",
                values['family'], values['revision'])

        # Check if all services exist
        response = connection.ecs.describe_services(
            cluster=cluster_name, services=task_definitions.keys())
        available_services = {
            service['serviceName'] for service in response['services']
        }
        new_services = set(task_definitions.keys()) - available_services

        #with lock_deployment(asg, asg_name):
            # with raise_available_capacity(asg, ec2, ecs, asg_name, cluster_name) as new_ec2_instance_id:
        with utils.downscale_services(connection, config['services'], cluster_name):

            # Update services
            for service_name, values in task_definitions.iteritems():

                if service_name in new_services:
                    logger.info("Creating new service %s with task defintion %s:%s",
                                service_name, values['family'], values['revision'])
                    connection.ecs.create_service(
                        cluster=cluster_name,
                        serviceName=service_name,
                        desiredCount=1,
                        taskDefinition='%s:%s' % (
                            values['family'], values['revision']))
                else:
                    logger.info("Updating service %s with task defintion %s:%s",
                                service_name, values['family'], values['revision'])
                    connection.ecs.update_service(
                        cluster=cluster_name,
                        service=service_name,
                        taskDefinition='%s:%s' % (
                            values['family'], values['revision']))

            logger.info("Waiting for deployments")
            # Wait till all service updates are deployed
            time.sleep(10)
            while True:
                response = connection.ecs.describe_services(
                    cluster=cluster_name, services=task_definitions.keys())
                time.sleep(5)
                if all(len(s['deployments']) == 1 for s in response['services']):
                    break


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
                    else:
                        container[key].update(value)

        return data


def write_task_definition(name, definition, output_path):
    filename = os.path.join(output_path, '%s.json' % name)
    with open(filename, 'wb') as fh:
        json.dump(definition, fh, indent=4)
