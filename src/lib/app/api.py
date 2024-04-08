import asyncio
import queue
import random
from http import HTTPStatus
from fastapi import FastAPI, Body, HTTPException
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn

from .worker import QueueWorker, QueueJob, QueueJobResult
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


async def initFastApi_():
    funcName = initFastApi_.__name__
    prefix = funcName
    try:
        ## Create a FastAPI instance
        api = FastAPI()

        ## Start a queue worker in separated thread
        startedPromise: asyncio.Future[bool] = asyncio.Future()
        worker = QueueWorker(startedPromise, 10)
        worker.start()

        ## await until worker is running
        await startedPromise

        @api.get("/hello")
        @api.post("/hello")
        async def hello(data: str = Body(..., embed=True)):
            return {"data": f"received data={data}!"}

        @api.post("/getInfo")
        async def get_info(data: str = Body(..., embed=True)):
            funcName = get_info.__name__
            prefix = funcName
            try:
                if data != "hello":
                    raise Exception("data is not hello")
                return {"data": f"received data={data}!"}
            except Exception as e:
                U.logPrefixE(prefix, e)

        @api.post("/put")
        async def put(data: str = Body(..., embed=True)):
            jobId = U.uuid()
            funcName = put.__name__
            prefix = f"{funcName}[{jobId}]"
            try:
                q = worker.jobQueue()
                U.logD(f"{prefix} putting to queue, count={q.qsize()}...")

                ## enqueue a job
                promise: asyncio.Future[QueueJobResult] = asyncio.Future()
                job: QueueJob = {
                    "createEpms": U.epochMs(),
                    "id": jobId,
                    "randomNo": random.randint(1, 10),
                    "message": f"hello-{jobId[-4:]}",
                    "promise": promise,
                }
                try:
                    ## if putting non-block (block=False), it will throw exception if queue is already full
                    q.put(job, block=False)
                    U.logD(f"{prefix} job successfully put, count={q.qsize()}")
                except queue.Full:
                    raise HTTPException(
                        status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=f"Service unavailable (job queue full)"
                    )

                ## await for result from worker
                MAX_WAIT_SEC = 5
                async with asyncio.timeout(MAX_WAIT_SEC):
                    result = await promise

                ## display result
                U.logD(f"{prefix} result[{jobId}]={result}")

                ## In case of error result
                if result["errCode"] != "":
                    raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"{result['err']}")

                return {"data": {"id": jobId, "result": result}}

            except Exception as e:
                throwHttpPrefix(prefix, jobId, e)

        return api
    except Exception as e:
        U.throwPrefix(prefix, e)


api = asyncio.run(initFastApi_())
