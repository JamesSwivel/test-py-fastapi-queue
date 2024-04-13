from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends

import util as U


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.get("/hello")
    @app.post("/hello")
    async def hello(data: str = Body(..., embed=True)):
        return {"data": f"received data={data}!"}

    @app.post("/getInfo")
    async def get_info(data: str = Body(..., embed=True)):
        funcName = get_info.__name__
        prefix = funcName
        try:
            if data != "hello":
                raise Exception("data is not hello")
            return {"data": f"received data={data}!"}
        except Exception as e:
            U.logPrefixE(prefix, e)
