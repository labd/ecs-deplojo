from ecs_deplojo.main import transform_definition


def test_definition(definition):
    definition['containerDefinitions'][0]['environment'] = {
        'DEBUG': True,
        'AWS_REGION': 'eu-west-1',
    }
    result = transform_definition(definition)

    assert result['containerDefinitions'][0]['environment'] == [
        {
            'name': 'AWS_REGION',
            'value': 'eu-west-1',
        },
        {
            'name': 'DEBUG',
            'value': 'True',
        },
    ]
