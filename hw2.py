from aiohttp import web, BasicAuth
import config
import Users
from FileManager import FileManager, EvalFailed
import asyncio
from urllib import parse


class Error404(web.Response):
    def __init__(self, path):
        with open('404.html', 'r') as html:
            body = html.read().format(path)
        super().__init__(status=404, body=body, headers={'Content-Type': 'text/html'})


class Error401(web.Response):
    def __init__(self):
        super().__init__(status=401, headers={"WWW-Authenticate": 'Basic realm="hw2-realm"'})


class Error403(web.Response):
    def __init__(self):
        super().__init__(status=403, headers={"WWW-Authenticate": 'Basic realm="hw2-realm"'})


async def readable_file(request):
    try:
        file = await FileManager().get_readable_file(request.path)
    except FileNotFoundError:
        return Error404(request.path)
    except PermissionError:
        return Error403()
    return web.FileResponse(path=file.path, headers={'Content-Type': file.mime_type})


async def dynamic_page(request):
    try:
        file = await FileManager().get_dynamic_page(request.path)
        rendered = file.render(user=request['user'], params=request.query)
    except FileNotFoundError:
        return Error404(request.path)
    except PermissionError:
        return Error403()
    return web.Response(body=rendered, headers={'Content-Type': 'text/html'})


async def admin_post(request):
    if not request['is_admin']:
        return Error401()
    try:
        post_line = await request.content.readline()
        post_line = post_line.decode('latin-1')
        user_param = dict(parse.parse_qs(post_line))
        username, password = user_param['username'], user_param['password']
        if len(username) > 1 or len(password) > 1:
            raise Exception
        username, password = parse.unquote(*username), parse.unquote(*password)
        user = Users.User(username, password)
    except:
        return web.Response(status=400)
    if user.username == request['user']['username']:
        return web.Response(status=409)
    try:
        with Users.Users() as users:
            users.insert(user)
    except Users.IntegrityError:
        return web.Response(status=409)
    return web.Response(body='OK')


async def admin_delete(request):
    if not request['is_admin']:
        return Error401()
    with Users.Users() as users:
        username = request.path_qs[len("/Users/"):]
        if '/' in username:
            return web.Response(status=400)
        rowcount = users.delete(parse.unquote(username))
    if rowcount:
        return web.Response()
    else:
        return web.Response(status=400)


async def authorization(request, handler):
    request['user'] = {'authenticated': False, 'username': None}
    request['is_admin'] = False
    auth_header = request.headers.get('Authorization')
    if auth_header:
        try:
            auth = BasicAuth.decode(auth_header)
        except ValueError:
            return Error401()
        request['user']['username'] = auth.login
        admin_good_login = auth.login == config.admin.get('username')
        admin_good_password = auth.password == config.admin.get('password')
        request['is_admin'] = admin_good_login and admin_good_password
        if request['is_admin']:
            request['user']['authenticated'] = True
        else:
            with Users.Users() as users:
                selected_user = users.select(auth.login)
            request['user']['authenticated'] = (selected_user and selected_user.password == auth.password)
    return await handler(request)


async def router(request):
    if request.method == 'GET':
        if request.path.endswith('.dp'):
            req_handler = dynamic_page
        else:
            return await readable_file(request)
    elif request.method == 'POST' and request.path == '/users':
        req_handler = admin_post
    elif request.method == 'DELETE' and request.path.startswith('/users/'):
        req_handler = admin_delete
    else:
        return web.Response(status=501)
    try:
        return await authorization(request, req_handler)
    except:
        return web.Response(status=500)


async def main():
    server = web.Server(router)
    runner = web.ServerRunner(server)
    await runner.setup()
    site = web.TCPSite(runner, host="localhost", port=config.port, shutdown_timeout=config.timeout)
    await site.start()

    print(f"======= Serving on {site.name} ======")

    # pause here for very long time by serving HTTP requests and
    # waiting for keyboard interruption
    await asyncio.sleep(100 * 3600)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    loop.close()
