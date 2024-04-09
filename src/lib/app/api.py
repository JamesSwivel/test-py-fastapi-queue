import asyncio
import queue
import random
from http import HTTPStatus
from fastapi import FastAPI, Body, HTTPException
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn

from .worker import QueueWorker, QueueJob, QueueJobResult, QueueJobType
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

        ## Start a message worker in separated thread
        messageWorkerStartedPromise: asyncio.Future[bool] = asyncio.Future()
        messageWorker = QueueWorker("messageWorker", messageWorkerStartedPromise, 10)
        messageWorker.start()

        ## Start a pool of pdf workers, each running in its own thread
        PDF_WORKER_COUNT = 8
        pdfWorkerStartedPromises = [asyncio.Future() for i in range(PDF_WORKER_COUNT)]
        pdfWorkers = [QueueWorker(f"pdfWorker{i+1}", pdfWorkerStartedPromises[i], 20) for i in range(PDF_WORKER_COUNT)]
        for i in range(PDF_WORKER_COUNT):
            pdfWorkers[i].start()

        ## await until workers are running
        await messageWorkerStartedPromise
        for i in range(PDF_WORKER_COUNT):
            await pdfWorkerStartedPromises[i]

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
        async def put(
            data: str = Body(..., embed=True),
            jobTypeStr: str = Body(embed=True, default=QueueJobType.MESSAGE, alias="jobType"),
        ):
            jobId = U.uuid()
            funcName = put.__name__
            prefix = f"{funcName}[{jobId}]"
            try:

                ## Default job type is message if not specified
                jobType: QueueJobType = QueueJobType.MESSAGE

                ## Default time waiting for worker result
                resultWaitSec = 5

                ## Check jobType
                jobQueue: queue.Queue[QueueJob]
                worker: QueueWorker
                if jobTypeStr == QueueJobType.MESSAGE:
                    jobType = QueueJobType.MESSAGE
                    jobQueue = messageWorker.jobQueue()
                    worker = messageWorker

                ## In case of pdf2image, it has longer result wait time, e.g. 60sec
                elif jobTypeStr == QueueJobType.PDF2IMAGE:
                    resultWaitSec = 60
                    jobType = QueueJobType.PDF2IMAGE

                    ## Find out the worker who is the least busy
                    worker = QueueWorker.leastBusyWorkers(pdfWorkers)
                    jobQueue = worker.jobQueue()
                else:
                    raise HTTPException(
                        status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=f"invalid job type={jobTypeStr}"
                    )

                U.logD(f"{prefix} [{worker.name()}] putting job to queue, count={jobQueue.qsize()}...")

                ## This is result promise that will be awaited until worker completes the task
                ## NOTE: This promise will be passed to the target worker queue
                resultPromise: asyncio.Future[QueueJobResult] = asyncio.Future()

                ## Construct a message job
                if jobType == QueueJobType.MESSAGE:
                    job: QueueJob = {
                        "createEpms": U.epochMs(),
                        "id": jobId,
                        "jobType": jobType,
                        "jobData": {
                            "tag": jobType,
                            "randomNo": random.randint(1, 10),
                            "message": f"{data}-{jobId[-4:]}",
                        },
                        "promise": resultPromise,
                    }
                    worker = messageWorker

                ## Construct a pdf2image job
                elif jobType == QueueJobType.PDF2IMAGE:
                    job: QueueJob = {
                        "createEpms": U.epochMs(),
                        "id": jobId,
                        "jobType": jobType,
                        "jobData": {
                            "tag": jobType,
                            ## This is the test pdf file, having 17 pages
                            "pdfFilePath": f"./data/regal-17pages.pdf",
                        },
                        "promise": resultPromise,
                    }

                ## Enqueue the job to target worker queue
                ## NOTE: if putting non-block (block=False), it will throw exception if queue is already full
                try:
                    jobQueue.put(job, block=False)
                    U.logD(f"{prefix} [{worker.name()}] job successfully submitted, count={jobQueue.qsize()}")
                except queue.Full:
                    raise HTTPException(
                        status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=f"Service unavailable (job queue full)"
                    )

                ## await for result from worker
                async with asyncio.timeout(resultWaitSec):
                    result = await resultPromise

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
