import pytest
from pytest_aiohttp import aiohttp_client, RawTestServer
from aiohttp import BasicAuth, web
import asyncio
import os
from hw2 import router
import Users
from config import admin as config_admin
from urllib import parse

class AdminAuth(BasicAuth):
    def __new__(cls):
        return super().__new__(cls, login=config_admin['username'], password=config_admin['password'])



@pytest.fixture
def cli(loop, aiohttp_client):
    with Users.Users() as users:
        users.delete_all()
        users.insert('Ofir', '1234')
    server = RawTestServer(router)
    return loop.run_until_complete(aiohttp_client(server))


async def test_unauthorized_get(cli):
    resp = await cli.get('/test.py')
    assert resp.status == 200


async def test_file_not_found(cli):
    resp = await cli.get('/not_found.txt')
    assert resp.status == 404


async def test_unauthorized_post(cli):
    resp = await cli.post('/users', data={"username": "unauthorized_post", "password": "1234"})
    assert resp.status == 401
    with Users.Users() as users:
        assert not users.select('unauthorized_post')


async def test_unauthorized_delete(cli):
    await cli.post('/users', auth=AdminAuth(), data={"username": "user1", "password": "1234"})
    resp = await cli.delete('/users/user1')
    assert resp.status == 401
    with Users.Users() as users:
        assert users.select('user1')


async def test_authorized_get(cli):
    resp = await cli.get('/test.py', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


async def test_multiget(cli):
    await asyncio.gather(*[test_authorized_get(cli) for _ in range(1000)])


async def test_admin_post_new(cli):
    await cli.delete('/users/user1', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": "user1", "password": "1234"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select('user1')


async def test_admin_post_backwords(cli):
    await cli.delete('/users/user1', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"password": "1234", "username": "user1"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select('user1')


async def test_admin_post_delete_gal(cli):
    username = "//:"
    for u in [username, parse.unquote(username)]:
        await cli.delete(f'/users/{u}', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": username, "password": "1234"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select(username)
    username = "%2F%2F%3A"
    await cli.delete(f'/users/{username}', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select(username)
        assert not users.select("//:")


async def test_admin_post_delete_no_slesh(cli):
    username = "@#$"
    await cli.delete(f'/users/{username}', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": username, "password": "1234"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select(username)
    await cli.delete(f'/users/{username}', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select(username)
    username = "%40%23%24"
    await cli.delete(f'/users/{username}', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select(username)
        assert not users.select("@#$")


async def test_admin_post_delete_special_chars(cli):
    username = r"user$@re$%&*djh(}].\"'/אכח"
    await cli.delete(f'/users/{username}', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": username, "password": "1234"})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select(username)
    await cli.delete(f'/users/{parse.quote(username, safe="")}', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select(parse.quote(username, safe=""))
        assert not users.select(username)


async def test_admin_post_special_chars_pas(cli):
    password = r"user$@re#$%&*djh(}].\"'/אכח"
    await cli.delete(f'/users/reut', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": "reut", "password": password})
    assert resp.status == 200
    with Users.Users() as users:
        assert users.select("reut")
    await cli.delete(f'/users/reut', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select("reut")


async def test_admin_post_nopass(cli):
    await cli.delete('/users/user1', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": "user1"})
    assert resp.status == 400
    with Users.Users() as users:
        assert not users.select('user1')


async def test_admin_post_empty_password(cli):
    await cli.delete('/users/user1', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": "user1", "password": ""})
    assert resp.status == 400
    with Users.Users() as users:
        assert not users.select('user1')


async def test_admin_post_empty_username(cli):
    await cli.delete('/users/user1', auth=AdminAuth())
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": "", "password": "233"})
    assert resp.status == 400
    with Users.Users() as users:
        assert not users.select('user1')


async def test_admin_post_integrity_error(cli):
    await cli.post('/users', auth=AdminAuth(),
                   data={"username": "user1", "password": "1234"})
    resp = await cli.post('/users', auth=BasicAuth(login='admin', password='admin'),
                          data={"username": "user1", "password": "1234"})
    assert resp.status == 409
    with Users.Users() as users:
        assert users.select('user1')


async def test_admin_post_admin(cli):#????????????????????????????????????????????????????????
    resp = await cli.post('/users', auth=AdminAuth(), data={"username": "admin", "password": "1234"})
    assert resp.status == 409
    with Users.Users() as users:
        assert not users.select('admin')


async def test_admin_delete(cli):
    await cli.post('/users', auth=AdminAuth(), data={"username": "user1", "password": "1234"})
    resp = await cli.delete('/users/user1', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select('user1')


async def test_admin_delete_slesh_false(cli):
    await cli.post('/users', auth=AdminAuth(), data={"username": "user1/reut/gol", "password": "1234"})
    resp = await cli.delete('/users/user1/reut/gol', auth=AdminAuth())
    assert resp.status == 400
    with Users.Users() as users:
        assert users.select('user1/reut/gol')


async def test_admin_delete_slesh_true(cli):
    await cli.post('/users', auth=AdminAuth(), data={"username": "user1/reut/gol", "password": "1234"})
    resp = await cli.delete('/users/user1%2Freut%2Fgol', auth=AdminAuth())
    assert resp.status == 200
    with Users.Users() as users:
        assert not users.select('user1/reut/gol')


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
    assert b"Ofir" in await resp.content.read()
    resp = await cli.get('example.dp?color=blue&number=42', auth=AdminAuth())
    assert resp.status == 200
    assert b"admin" in await resp.content.read()
    resp = await cli.get('example.dp?color=blue&number=42', auth=BasicAuth(login='Ofir', password='12345'))
    assert resp.status == 200
    assert b"Please authenticate so we\'ll know your name" in await resp.content.read()
    resp = await cli.get('folder/example2.dp?color=blue&number=42', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200
    resp = await cli.get('example2.dp?color=blue&number=42', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 404
    resp = await cli.get('empty.dp', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


async def test_forbidden_page(cli):
    resp = await cli.get('config.py', auth=AdminAuth())
    assert resp.status == 403
    resp = await cli.get('config.py', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 403
    resp = await cli.get('config.py')
    assert resp.status == 403
    resp = await cli.get('users.db', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 403
    resp = await cli.get('mime.json', auth=BasicAuth(login='Ofir', password='1234'))
    assert resp.status == 200


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


async def test_concurrency_test_db_access(aiohttp_client):
    async def sleep(request):
        with Users.Users():
            pass
        return web.Response(body='OK')

    server = RawTestServer(sleep)
    client = await aiohttp_client(server)
    url = "//" + client.host + ':' + str(client.port) + '/sleep_db'
    tasks = [client.session.get(url, auth=BasicAuth(login='Ofir', password='1234')) for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    for resp in responses:
        assert resp.status == 200