from fastapi import FastAPI
import util as U
from util.fastApi import useExceptionHandlerMiddleware

def initAllEndpoints(app: FastAPI):
    funcName = initAllEndpoints.__name__
    prefix = funcName
    try:

        ## init and use global exception error handler
        useExceptionHandlerMiddleware(app)

        from .simple import initEndpoints

        initEndpoints(app)
        from .uploadFile import initEndpoints

        initEndpoints(app)
        from .multi import initEndpoints

        initEndpoints(app)

        from .dynamicPayload import initEndpoints

        initEndpoints(app)
    except Exception as e:
        U.throwPrefix(prefix, e)
