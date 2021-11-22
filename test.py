import pytest
from AsyncServer import MyApp
from pytest_aiohttp import aiohttp_client, TestClient
from aiohttp import BasicAuth, web
import asyncio
import Users
import os


@pytest.fixture
def cli(loop, aiohttp_client):
    app = MyApp()
    return loop.run_until_complete(aiohttp_client(app))


async def test_unauthorized_get(cli):
    resp = await cli.get('/')
    assert resp.status == 401


async def test_unauthorized_post(cli):
    resp = await cli.post('/users', data={"username": "unauthorized_post", "password": "1234"})
    assert resp.status == 401
    with Users.Users() as users:
        assert not users.select('unauthorized_post')


async def test_unauthorized_delete(cli):
    resp = await cli.delete('/users/admin')
    assert resp.status == 401
    with Users.Users() as users:
        assert users.select('admin')


async def test_authorized_get(cli):
    resp = await cli.get('/', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


async def test_multiget(cli):
    await asyncio.gather(*[test_authorized_get(cli) for _ in range(1000)])


async def test_admin_post(cli):
    resp = await cli.post('/users', auth=BasicAuth(login='admin', password='admin'),
                          data={"username": "user1", "password": "1234"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select('user1')


async def test_admin_delete(cli):
    resp = await cli.delete('/users/user1', auth=BasicAuth(login='admin', password='admin'))
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select('user1')


async def test_image(cli):
    for file in os.listdir('Thailand'):
        resp = await cli.get(f'/Thailand/{file}', auth=BasicAuth(login='Ofir', password='1234'))
        assert resp.status == 200
        assert int(resp.headers['Content-Length']) > 10000


async def test_concurrency_test(aiohttp_client):
    app = MyApp()

    async def sleep(request):
        await asyncio.sleep(1)
        print('sleeping...')
        return web.Response(body='OK')

    app.router.add_get('/sleep', sleep)
    client = await aiohttp_client(app)
    url = "//" + client.host + ':' + str(client.port) + '/sleep'
    print(url)
    tasks = [client.session.get(url, auth=BasicAuth(login='Ofir', password='1234')) for _ in range(100)]
    responses = await asyncio.gather(*tasks)
    for resp in responses:
        assert resp.status == 200

# async def test_set_value(cli):
#     resp = await cli.post('/', data={'value': 'foo'})
#     assert resp.status == 200
#     assert await resp.text() == 'thanks for the data'
#     assert cli.server.app['value'] == 'foo'
#
# async def test_get_value(cli):
#     cli.server.app['value'] = 'bar'
#     resp = await cli.get('/')
#     assert resp.status == 200
#     assert await resp.text() == 'value: bar'
