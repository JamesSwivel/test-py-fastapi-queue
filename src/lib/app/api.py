import asyncio
from fastapi import FastAPI, Body
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any

from .worker import QueueWorker, QueueItem
import util as U


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
            funcName = put.__name__
            prefix = funcName
            try:
                q = worker.jobQueue()
                U.logD(f"{prefix}| putting to queue, count={q.qsize()}...")

                ## enqueue an item
                promise = asyncio.Future()
                uuid = U.uuid()
                item: QueueItem = {"id": uuid, "message": f"hello-{uuid[-4:]}", "promise": promise}
                q.put(item, block=False)
                U.logD(f"{prefix}| Item successfully put, , count={q.qsize()}")

                ## await for result from worker
                result = await promise
                U.logD(f"{prefix}| result[{uuid}]={result}")
                return {"data": {"id": uuid, "result": result}}
            except Exception as e:
                U.logPrefixE(prefix, e)

        return api
    except Exception as e:
        U.throwPrefix(prefix, e)


api = asyncio.run(initFastApi_())
