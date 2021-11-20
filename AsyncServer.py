from aiohttp import web, BasicAuth
import config

async def readable_file(request):
    return web.FileResponse(status=200, path='text.txt',
                            headers={'Content-Type': "text/plain"})


@web.middleware
async def middleware(request, handler):
    auth_header = request.headers.get('Authorization')
    if auth_header:
        auth = BasicAuth.decode(auth_header)
        print(auth)
        if auth.login == 'ofir' and auth.password == '123':
            print(f'{auth.login} is Authorized')
            return await handler(request)
    response = web.Response(status=401, headers={"WWW-Authenticate": 'Basic realm="hw2-realm"'})
    return response

if __name__ == '__main__':
    app = web.Application(middlewares=[middleware])
    app.router.add_get('/', readable_file)
    web.run_app(app, host="localhost", port=config.port, shutdown_timeout=config.timeout)
