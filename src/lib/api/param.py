import os
from typing import Optional, Annotated, NotRequired
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends, Request, Query, Path
from fastapi.exceptions import ResponseValidationError
from pydantic import BaseModel, Field, validator


import util as U
from util.fastApi import throwHttpPrefix


class RequestData_(BaseModel):
    data: Annotated[str, Field(...)]
    message: Annotated[str, Field(None, min_length=5)]


class ResponseData_(BaseModel):
    data: str


"""
NOTE:
https://fastapi.tiangolo.com/tutorial/query-params-str-validations/
- For path and query params, not need to define BaseModel
- BaseModel is mostly used for request and response payload
"""


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.post(
        "/pathParam/{action}/{id}",
        description="This is an API that makes use of path/route as input parameters",
    )
    async def pathParam(
        action: Annotated[str, Path(max_length=4, min_length=4, description="This is the action, e.g. SEND")],
        id: Annotated[int, Path(description="This is the id to perform the action")],
        data: RequestData_,
        param1: Annotated[str | None, Query(alias="s1")] = None,
        param2: Annotated[str | None, Query(alias="s2")] = None,
    ):
        funcName = pathParam.__name__
        prefix = funcName
        try:
            res = {
                "pathParams": {"action": action, "id": id},
                "queryParams": {"s1": param1, "s2": param2},
                "payloadData": data,
            }
            return res
        except Exception as e:
            throwHttpPrefix(prefix, e)
