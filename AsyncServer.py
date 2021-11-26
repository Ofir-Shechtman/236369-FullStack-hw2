from aiohttp import web, BasicAuth
import config
import Users
from FileManager import FileManager, BadExtension, EvalFailed
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
    # if not request['user']['authenticated']:
    #     return Error401()
    try:
        file = await file_manager.get_readable_file(request.path)
    except (PermissionError, FileNotFoundError):
        return Error404(request.path)
    return web.FileResponse(path=file.path, headers={'Content-Type': file.mime_type})


async def dynamic_page(request):
    try:
        file = await file_manager.get_dynamic_page(request.path)
        rendered = file.render(user=request['user'], params=request.query)
    except (PermissionError, FileNotFoundError):
        return Error404(request.path)
    except EvalFailed:
        return web.Response(status=500)
    return web.Response(body=rendered, headers={'Content-Type': 'text/html'})


async def admin_post(request):
    if not request['is_admin']:
        return Error403()
    post_line = await request.content.readline()
    post_line = post_line.decode('latin-1')
    user = Users.User(*dict(parse.parse_qsl(post_line)))
    try:
        with Users.Users() as users:
            users.insert(user)
            users.commit()
    except Users.IntegrityError:
        return web.Response(status=409)
    return web.Response(body='OK')


async def admin_delete(request):
    if not request['is_admin']:
        return Error403()
    # print("DELETE")
    with Users.Users() as users:
        rowcount = users.delete(request.match_info['username'])
        users.commit()
    # print(f'{rowcount} deleted')
    if rowcount:
        return web.Response(body='OK')
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
            req_handler = readable_file
    elif request.method == 'POST' and request.path == '/users':
        req_handler = admin_post
    elif request.method == 'DELETE' and request.path.startswith('/users/'):
        req_handler = admin_delete
    else:
        return Error404(request.path)
    return await authorization(request, req_handler)


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
    file_manager = FileManager()
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    loop.close()
