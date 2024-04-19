import asyncio
from http import HTTPStatus
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import HTTPException, FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn, Annotated
import util as U


def useExceptionHandlerMiddleware(app: FastAPI):
    '''
    Use global exception handler for FastAPI
    - If the endpoint has no try/except block to handle exception, this will handle
    - This also suppresses messy error messages from the ASGI layer, e.g.
      ERROR:    Exception in ASGI application
    '''
    funcName = useExceptionHandlerMiddleware.__name__
    prefix = funcName
    try:
        class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    return await call_next(request)
                except Exception as e:
                    U.logPrefixE(f"{ExceptionHandlerMiddleware.__name__}", e)
                    return JSONResponse(
                        status_code=500, 
                        content={
                            'error': e.__class__.__name__, 
                            'messages': U.Log.toExceptionStr(e)
                        }
                    )
        app.add_middleware(ExceptionHandlerMiddleware)
        U.logW(f"Use middleware[{ExceptionHandlerMiddleware.__name__}]")
    except Exception as e:
        U.logPrefixE(prefix,e)


## A helper function to raise HTTPException
def throwHttpPrefix(prefix: str, e: Union[Exception, str], id: str = "") -> NoReturn:
    ## empty id -> "--"
    if id == "":
        id = "--"

    ## default is 500 internal server error
    httpStatusCode = HTTPStatus.INTERNAL_SERVER_ERROR
    httpErr = f"[{id}] internal server error"

    internalErrStr = U.Log.toExceptionStr(e)
    if isinstance(e, HTTPException):
        internalErrStr = e.detail
        httpStatusCode = e.status_code
        httpErr = f"[{id}] {internalErrStr}"
    elif isinstance(e, asyncio.TimeoutError):
        internalErrStr = f"gateway timeout (async await)"
        httpStatusCode = HTTPStatus.GATEWAY_TIMEOUT
        httpErr = f"[{id}] {internalErrStr}"

    ## print internal error (not exposed to http response)
    U.logPrefixE(prefix, internalErrStr)

    ## raise HTTPException (visible to public)
    raise HTTPException(status_code=httpStatusCode, detail=httpErr)


