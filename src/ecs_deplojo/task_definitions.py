import json
import os.path
from string import Template


def generate_task_definitions(config, template_vars, base_path,
                              output_path=None):
    """Generate the task definitions

    :parameter config: The yaml config contents
    :parameter template_vars: Key-Value dict with template replacements
    :parameter base_path: The base path (location of the config file)
    :parameter output_path: Optional path to write the task definitions to.
    :rtype dict:

    """
    task_definitions = {}

    for name, info in config['task_definitions'].items():
        # Default environment. Always create a new dict instance since it is
        # mutated.
        env_items = {}
        env_items.update(config.get('environment', {}))

        # Environment groups
        env_group = info.get('environment_group')
        if env_group:
            env_items.update(config['environment_groups'][env_group])

        overrides = info.get('overrides', {})
        definition = generate_task_definition(
            info['template'],
            env_items,
            template_vars,
            overrides,
            name=name,
            base_path=base_path)

        if output_path:
            write_task_definition(name, definition, output_path)
        task_definitions[name] = {
            'definition': definition,
        }
    return task_definitions


def generate_task_definition(filename, environment, template_vars, overrides,
                             name, base_path=None):

    """Generate the task definitions"""
    if base_path:
        filename = os.path.join(base_path, filename)

    with open(filename, 'r') as fh:
        data = json.load(fh)

        data['family'] = name
        for container in data['containerDefinitions']:
            container['image'] = Template(container['image']).substitute(template_vars)
            container['environment'] = environment

            if overrides:
                container_overrides = overrides.get(container['name'], {})
                for key, value in container_overrides.items():
                    if key in container and isinstance(container[key], list):
                        container[key].extend(value)
                    elif key in container and isinstance(container[key], dict):
                        container[key].update(value)
                    else:
                        container[key] = value

        return data


def write_task_definition(name, definition, output_path):
    filename = os.path.join(output_path, '%s.json' % name)
    with open(filename, 'w') as fh:
        json.dump(definition, fh, indent=4)
