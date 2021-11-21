from aiohttp import web, BasicAuth
import config
import Users


async def readable_file(request):
    return web.FileResponse(status=200, path='text.txt',
                            headers={'Content-Type': "text/plain"})


@web.middleware
async def middleware(request, handler):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth = BasicAuth.decode(auth_header)
        print(auth)
        user = app['database'].select(auth.login)
        print(user)
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


if __name__ == '__main__':
    app = web.Application(middlewares=[middleware])
    app.on_startup.append(connect_db)
    app.on_cleanup.append(disconnect_db)
    app.router.add_get('/', readable_file)
    web.run_app(app, host="localhost", port=config.port, shutdown_timeout=config.timeout)
