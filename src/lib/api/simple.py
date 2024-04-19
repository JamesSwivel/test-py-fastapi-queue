import os
from typing import Optional
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends, Request
from fastapi.exceptions import ResponseValidationError
from pydantic import BaseModel, Field, validator
import pdf2image

import util as U
from util.fastApi import throwHttpPrefix
from .worker.types import QueueJobResult


class SimpleRes(BaseModel):
    data: str


def onJobPdf2image(jobId: str, jobResult: QueueJobResult):
    funcName = onJobPdf2image.__name__
    prefix = f"{funcName}[{jobId}]"
    try:
        pdfPath = f"./data/regal-17pages.pdf"
        U.logD(f"{prefix} converting {pdfPath}")
        pages = pdf2image.convert_from_path(pdfPath, thread_count=4)
        if pages is not None and len(pages) > 0:
            basedDir = f"./out/pdf2image/{jobId}"
            os.makedirs(basedDir)
            for idx, page in enumerate(pages):
                page.save(f"{basedDir}/image-{idx:0>2}.png")
        jobResult["data"] = f"pdf2image finished ({U.epochMs()}), nPages={len(pages)}"
        U.logD(f"{prefix} finished")
    except Exception as e:
        U.logPrefixE(prefix, e)
        U.throwPrefix(prefix, e)


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.get(
        "/hello",
        response_model=SimpleRes,
        description="This is most basic API that echoes the data you requested!<br>Have Fun and try it out!!",
    )
    @app.post("/hello", response_model=SimpleRes)
    async def hello(data: str = Body(..., embed=True)):
        funcName = hello.__name__
        prefix = funcName
        try:
            res = {"data": f"received data={data}!", "password": "secret"}
            return res
        except Exception as e:
            throwHttpPrefix(prefix, e)

    @app.post("/helloNoExceptionHandling", response_model=SimpleRes)
    async def helloNoExceptionHandling(data: str = Body(..., embed=True)):
        if data == "throw":
            raise Exception(f"requested to throw exception")
        res = {"data": f"received data={data}!", "password": "secret"}
        return res

    ## NOTE: include_in_schema=False to hide endpoint shown in the swagger
    @app.post("/helloHidden", response_model=SimpleRes, include_in_schema=False)
    async def helloHidden(data: str = Body(..., embed=True)):
        if data == "throw":
            raise Exception(f"requested to throw exception")
        res = {"data": f"received data={data}!", "password": "secret"}
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

    @app.post("/pdf2image", response_model=SimpleRes)
    async def postPdf2image(data: str = Body(..., embed=True)):
        funcName = postPdf2image.__name__
        prefix = funcName
        try:
            jobId = U.uuid()
            jobResult: QueueJobResult = {
                "errCode": "",
                "err": "",
                "data": "",
                "workerName": "test",
                "dequeueElapsedMs": 0,
                "processElapsedMs": 0,
                "totalElapsedMs": 0,
            }
            onJobPdf2image(jobId, jobResult)
            return jobResult
        except Exception as e:
            throwHttpPrefix(prefix, e)
