from typing import (
    Final,
    Union,
    Callable,
    TypeVar,
    List,
    TypedDict,
    Dict,
    Any,
    NoReturn,
    Annotated,
    Optional,
    NotRequired,
)
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel, Field, validator

import util as U


class PayloadHeader(BaseModel):
    id: str = Field(..., description="payload id")
    messages: List[str] = Field(..., description="payload message")

    @validator("id")
    def checkId(cls, v: str):
        isValid = U.isUuid(v)
        if not isValid:
            raise ValueError(f"invalid value (id is not uuid)")
        return v


class PayloadBody(BaseModel):
    value: int = Field(..., description="payload value")

    ## Optional + Field(...) means extra must exist but can be null
    extra: Optional[str] = Field(..., description="payload extra")

    ## Optional + Field(None) means extra may be missing and default value is None
    ## https://stackoverflow.com/questions/67569529/using-fastapi-pydantic-how-do-i-define-an-optional-field-with-a-description
    extra2: Optional[str] = Field(None, description="payload extra2")

    @validator("value")
    def checkValue(cls, v: Any) -> bool:
        isValid = v >= 1 and v <= 10
        if not isValid:
            raise ValueError(f"invalid value (not in range of 1 to 10)")
        return v


class PayloadHeaderBody(BaseModel):
    header: PayloadHeader
    data: PayloadBody


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.post("/payloadSimple")
    async def payloadSimple(data: PayloadHeader = Body(...)):
        funcName = payloadSimple.__name__
        prefix = funcName
        try:
            return {"data": data}
        except Exception as e:
            U.logPrefixE(prefix, e)

    @app.post("/payloadOptional")
    async def payloadOptional(data: PayloadBody = Body(...)):
        funcName = payloadOptional.__name__
        prefix = funcName
        try:
            return {"data": data}
        except Exception as e:
            U.logPrefixE(prefix, e)

    @app.post("/payloadFull")
    async def payloadFull(data: PayloadHeaderBody = Body(...)):
        funcName = payloadFull.__name__
        prefix = funcName
        try:
            return {"data": data}
        except Exception as e:
            U.logPrefixE(prefix, e)
