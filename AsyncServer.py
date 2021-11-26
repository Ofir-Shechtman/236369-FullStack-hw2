from aiohttp import web, BasicAuth
import config
import Users
from FileManager import FileManager, BadExtension, EvalFailed


async def index(request):
    if not request['user']['authenticated']:
        return Error401()
    return web.Response(body='OK')


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
    if not request['user']['authenticated']:
        return Error401()
    fm = request.app['file_manager']
    try:
        file = await fm.get_readable_file(request.path)
    except (PermissionError, FileNotFoundError):
        return Error404(request.path)
    return web.FileResponse(path=file.path, headers={'Content-Type': file.mime_type})


async def dynamic_page(request):
    fm = request.app['file_manager']
    try:
        file = await fm.get_dynamic_page(request.path)
        rendered = file.render(user=request['user'], params=request.query)
    except (PermissionError, FileNotFoundError):
        return Error404(request.path)
    except EvalFailed:
        return web.Response(status=500)
    return web.Response(body=rendered, headers={'Content-Type': 'text/html'})


async def admin_post(request):
    if not request['is_admin']:
        return Error403()
    # print("POST")
    post_line = await request.content.readline()
    post_line = post_line.decode('latin-1')
    user = Users.User(*[param.split('=')[1] for param in post_line.split('&')])
    # print(user)
    try:
        with Users.Users() as users:
            users.insert(user)
            users.commit()
    except Users.IntegrityError:
        return web.Response(status=400)
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


@web.middleware
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
            # print(f'Admin login')
        else:
            with Users.Users() as users:
                selected_user = users.select(auth.login)
            request['user']['authenticated'] = (selected_user and selected_user.password == auth.password)
            # if request['user']['authenticated']:
            #     print(f'{auth.login} is Authorized')
    return await handler(request)


async def connect_db(app):
    app['file_manager'] = FileManager()


class MyApp(web.Application):
    def __init__(self):
        super().__init__(middlewares=[authorization])
        self.on_startup.append(connect_db)
        self.router.add_get('/', index)
        self.router.add_get('/{file_path:.+}.dp', dynamic_page)
        self.router.add_get('/{file_path:.+}.{ext:.+}', readable_file)
        self.router.add_post('/users', admin_post)
        self.router.add_delete('/users/{username:.+}', admin_delete)


if __name__ == '__main__':
    app = MyApp()
    web.run_app(app, host="localhost", port=config.port, shutdown_timeout=config.timeout)
