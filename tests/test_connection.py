from ecs_deplojo.main import Connection


def test_clients():
    connection = Connection()

    assert connection.ecs
