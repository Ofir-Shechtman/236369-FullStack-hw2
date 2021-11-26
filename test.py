import pytest
from pytest_aiohttp import aiohttp_client,  RawTestServer
from aiohttp import BasicAuth, web
import asyncio
import Users
import os
from AsyncServer import router


@pytest.fixture
def cli(loop, aiohttp_client):
    server = RawTestServer(router)
    return loop.run_until_complete(aiohttp_client(server))


async def test_unauthorized_get(cli):
    resp = await cli.get('/test.py')
    assert resp.status == 200


async def test_unauthorized_post(cli):
    resp = await cli.post('/users', data={"username": "unauthorized_post", "password": "1234"})
    assert resp.status == 403
    with Users.Users() as users:
        assert not users.select('unauthorized_post')


async def test_unauthorized_delete(cli):
    resp = await cli.delete('/users/admin')
    assert resp.status == 403
    with Users.Users() as users:
        assert users.select('admin')


async def test_authorized_get(cli):
    resp = await cli.get('/test.py', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


async def test_multiget(cli):
    await asyncio.gather(*[test_authorized_get(cli) for _ in range(1000)])


async def test_admin_post_new(cli):
    await cli.delete('/users/user1', auth=BasicAuth(login='admin', password='admin'))
    resp = await cli.post('/users', auth=BasicAuth(login='admin', password='admin'),
                          data={"username": "user1", "password": "1234"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select('user1')


async def test_admin_post_integrity_error(cli):
    await cli.post('/users', auth=BasicAuth(login='admin', password='admin'),
                   data={"username": "user1", "password": "1234"})
    resp = await cli.post('/users', auth=BasicAuth(login='admin', password='admin'),
                          data={"username": "user1", "password": "1234"})
    assert resp.status == 409
    with Users.Users() as users:
        assert users.select('user1')


async def test_admin_delete(cli):
    await cli.post('/users', auth=BasicAuth(login='admin', password='admin'),
                   data={"username": "user1", "password": "1234"})
    resp = await cli.delete('/users/user1', auth=BasicAuth(login='admin', password='admin'))
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select('user1')


async def test_image(cli):
    for file in os.listdir('Thailand'):
        resp = await cli.get(f'/Thailand/{file}', auth=BasicAuth(login='Ofir', password='1234'))
        assert resp.status == 200
        assert int(resp.headers['Content-Length']) > 10000


async def test_dynamic_page(cli):
    resp = await cli.get('example.dp', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 500
    resp = await cli.get('example.dp?color=blue&number=42', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200
    resp = await cli.get('folder/example2.dp?color=blue&number=42', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200
    resp = await cli.get('example2.dp?color=blue&number=42', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 404
    resp = await cli.get('empty.dp', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


async def test_forbidden_page(cli):
    resp = await cli.get('config.py', auth=BasicAuth(login='admin', password='admin'))
    assert resp.status == 403
    resp = await cli.get('config.py', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 403
    resp = await cli.get('users.db', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 403
    resp = await cli.get('mime.json', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


@pytest.mark.timeout(2)
async def test_concurrency_test(aiohttp_client):
    async def sleep(request):
        await asyncio.sleep(1)
        # print('sleeping...')
        return web.Response(body='OK')

    server = RawTestServer(sleep)
    client = await aiohttp_client(server)
    url = "//" + client.host + ':' + str(client.port) + '/sleep'
    tasks = [client.session.get(url, auth=BasicAuth(login='Ofir', password='1234')) for _ in range(100)]
    responses = await asyncio.gather(*tasks)
    for resp in responses:
        assert resp.status == 200

