import asyncio
from http import HTTPStatus
from fastapi import HTTPException, FastAPI
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn, Annotated
import util as U


## A helper function to raise HTTPException
def throwHttpPrefix(prefix: str, id: str, e: Union[Exception, str]) -> NoReturn:
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


def initAllEndpoints(app: FastAPI):
    funcName = initAllEndpoints.__name__
    prefix = funcName
    try:
        from .simple import initEndpoints

        initEndpoints(app)
        from .uploadFile import initEndpoints

        initEndpoints(app)
        from .multiThread import initEndpoints

        initEndpoints(app)
    except Exception as e:
        U.throwPrefix(prefix, e)
