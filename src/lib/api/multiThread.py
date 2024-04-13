import queue
import random
import asyncio
from http import HTTPStatus
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends

import util as U
from app import FastApiServer
from .util import throwHttpPrefix
from .worker.mTWorker import MultiThreadQueueWorker, QueueJob, QueueJobResult, QueueJobType


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    @app.post("/multiThread")
    async def multiThread(
        data: str = Body(..., embed=True),
        jobTypeStr: str = Body(embed=True, default=QueueJobType.MESSAGE, alias="jobType"),
    ):
        jobId = U.uuid()
        funcName = multiThread.__name__
        prefix = f"{funcName}[{jobId}]"
        try:

            ## Default job type is message if not specified
            jobType: QueueJobType = QueueJobType.MESSAGE

            ## Default time waiting for worker result
            resultWaitSec = 5

            ## Check jobType
            jobQueue: queue.Queue[QueueJob]
            if jobTypeStr == QueueJobType.MESSAGE:
                jobType = QueueJobType.MESSAGE
                jobQueue = FastApiServer.messageWorker.jobQueue()

            ## In case of pdf2image, it has longer result wait time, e.g. 60sec
            elif jobTypeStr == QueueJobType.PDF2IMAGE:
                resultWaitSec = 60
                jobType = QueueJobType.PDF2IMAGE

                ## Find out queue that it is least busy from the workers
                ## NOTE: queue can be shared by multiple workers
                jobQueue = MultiThreadQueueWorker.leastBusyWorkers(FastApiServer.pdfWorkers).jobQueue()
            else:
                raise HTTPException(
                    status_code=HTTPStatus.UNPROCESSABLE_ENTITY, detail=f"invalid job type={jobTypeStr}"
                )

            U.logD(f"{prefix} putting job to queue, count={jobQueue.qsize()}...")

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
                U.logD(f"{prefix} job successfully submitted, count={jobQueue.qsize()}")
            except queue.Full:
                raise HTTPException(
                    status_code=HTTPStatus.SERVICE_UNAVAILABLE, detail=f"Service unavailable (job queue full)"
                )

            ## await for result from worker
            async with asyncio.timeout(resultWaitSec):
                result = await resultPromise

            ## display result
            U.logD(f"{prefix} result={result}")

            ## In case of error result
            if result["errCode"] != "":
                raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"{result['err']}")

            return {"data": {"id": jobId, "result": result}}

        except Exception as e:
            throwHttpPrefix(prefix, jobId, e)
