from typing import Optional
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel, Field, validator

import util as U
from .util import throwHttpPrefix


class SimpleRes(BaseModel):
    data: str


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.get("/hello", response_model=SimpleRes)
    @app.post("/hello", response_model=SimpleRes)
    async def hello(data: str = Body(..., embed=True)):
        res = {"data": f"received data={data}!"}
        return res

    @app.post("/getInfo", response_model=SimpleRes)
    async def get_info(data: str = Body(..., embed=True)):
        funcName = get_info.__name__
        prefix = funcName
        try:
            if data != "hello":
                raise Exception("data is not hello")

            res = {"data": f"received data={data}!"}
            return res
        except Exception as e:
            throwHttpPrefix(prefix, e)
