from aiohttp import web
from config import port


async def file(request):
    return web.FileResponse(path='config.py', headers={'Content-Type': 'text/plain'})


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([web.get('/', file)])
    web.run_app(app, host='localhost', port=port)
