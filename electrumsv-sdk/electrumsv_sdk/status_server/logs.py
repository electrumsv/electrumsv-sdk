import logging

def trinket_logging_setup(app, level=logging.DEBUG):
    logger = logging.getLogger('trinket')

    @app.listen('request')
    async def log_request(request):
        logger.info('%s %s', request.method, request.url.decode())

    @app.listen('startup')
    async def startup():
        pass

    @app.listen('shutdown')
    async def shutdown():
        pass

    return app
