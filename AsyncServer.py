from aiohttp import web, BasicAuth
import config
import Users
from FileManager import FileManager

async def readable_file(request):
    # TODO Create files folders and set MIME support
    file = FileManager.get(request.path)
    return web.FileResponse(status=200, path=file.path,
                            headers={'Content-Type': file.mime_type})


@web.middleware
async def authorization(request, handler):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth = BasicAuth.decode(auth_header)
        print(auth)
        # TODO admin check for post&delete
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


async def disconnect_db(app):
    app['database'].close()
    print("DB closed")


class MyApp(web.Application):
    def __init__(self):
        super().__init__(middlewares=[authorization])
        self.on_startup.append(connect_db)
        self.on_cleanup.append(disconnect_db)
        self.router.add_get('/folder/text.txt', readable_file)

if __name__ == '__main__':
    app = MyApp()
    web.run_app(app, host="localhost", port=config.port, shutdown_timeout=config.timeout)
