from aiohttp import web, BasicAuth
import config
import Users
from FileManager import FileManager


async def index(request):
    return web.Response(body='OK')


async def readable_file(request):
    fm = request.app['file_manager']
    try:
        file = await fm.get_readable_file(request.path)
    except (PermissionError, FileNotFoundError):
        with open('404.html', 'r') as html:
            body = html.read().format(request.path)
        return web.Response(status=404, body=body, headers={'Content-Type': 'text/html'})
    return web.FileResponse(path=file.path, headers={'Content-Type': file.mime_type})


async def dynamic_page(request):
    file = await FileManager.get(request.path)
    return web.FileResponse(path=file.path, headers={'Content-Type': file.mime_type})


async def admin_post(request):
    print("POST")
    post_line = await request.content.readline()
    post_line = post_line.decode('latin-1')
    user = Users.User(*[param.split('=')[1] for param in post_line.split('&')])
    print(user)
    try:
        request.app['database'].insert(user)
        request.app['database'].commit()
    except Users.IntegrityError as e:
        print(e)
    return web.Response(body='OK')


async def admin_delete(request):
    print("DELETE")
    rowcount = request.app['database'].delete(request.match_info['username'])
    request.app['database'].commit()
    print(f'{rowcount} deleted')
    return web.Response(body='OK')


@web.middleware
async def authorization(request, handler):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth = BasicAuth.decode(auth_header)
        print(auth)
        if auth.login == config.admin.get('username') and auth.password == config.admin.get('password'):
            print(f'Admin login')
            return await handler(request)
        elif request.method == "GET":
            user = request.app['database'].select(auth.login)
            if user and user.password == auth.password:
                print(f'{auth.login} is Authorized')
                return await handler(request)
    response = web.Response(status=401, headers={"WWW-Authenticate": 'Basic realm="hw2-realm"'})
    return response


async def connect_db(app):
    print("Connecting DB...")
    app['database'] = Users.Users()
    print(app['database'])
    app['file_manager'] = FileManager()


async def disconnect_db(app):
    app['database'].close()
    print("DB closed")


class MyApp(web.Application):
    def __init__(self):
        super().__init__(middlewares=[authorization])
        self.on_startup.append(connect_db)
        self.on_cleanup.append(disconnect_db)
        self.router.add_get('/', index)
        self.router.add_get('/{file_path:.+}', readable_file)
        self.router.add_get('/{file_path:.+}.dp', dynamic_page)
        self.router.add_post('/users', admin_post)
        self.router.add_delete('/users/{username:.+}', admin_delete)


if __name__ == '__main__':
    app = MyApp()
    web.run_app(app, host="localhost", port=config.port, shutdown_timeout=config.timeout)
