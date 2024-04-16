from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn, Annotated, Optional
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel

import util as U


class PayloadSimple(BaseModel):
    id: str
    value: int
    messages: List[str]
    extra: Optional[str]


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.post("/payloadSimple")
    async def payloadSimple(data: PayloadSimple = Body(...)):
        funcName = payloadSimple.__name__
        prefix = funcName
        try:
            return {"data": data}
        except Exception as e:
            U.logPrefixE(prefix, e)
