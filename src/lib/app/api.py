import os
import asyncio
import queue
import random
from dataclasses import dataclass
from http import HTTPStatus
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from pydantic import BaseModel
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn, Annotated

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
        MESSAGE_WORKER_MAX_QSIZE = 10
        messageWorkerStartedPromise: asyncio.Future[bool] = asyncio.Future()
        messageWorker = QueueWorker(
            "messageWorker", messageWorkerStartedPromise, {"queueMaxSize": MESSAGE_WORKER_MAX_QSIZE}
        )
        messageWorker.start()

        ## Start a pool of pdf workers, each running in its own thread
        PDF_WORKER_MAX_QSIZE = 10
        PDF_WORKER_COUNT = 8
        IS_PDF_WORKER_SINGLE_QUEUE = True
        if IS_PDF_WORKER_SINGLE_QUEUE:
            U.logW(f"Use single queue for pdf worker!")
            pdfWorkerSingleQueue = queue.Queue()
        pdfWorkerStartedPromises = [asyncio.Future() for i in range(PDF_WORKER_COUNT)]
        pdfWorkers = [
            QueueWorker(
                f"pdfWorker{i+1}",
                pdfWorkerStartedPromises[i],
                {
                    "queueMaxSize": PDF_WORKER_MAX_QSIZE,
                    "queue": pdfWorkerSingleQueue if IS_PDF_WORKER_SINGLE_QUEUE else None,
                },
            )
            for i in range(PDF_WORKER_COUNT)
        ]
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
                if jobTypeStr == QueueJobType.MESSAGE:
                    jobType = QueueJobType.MESSAGE
                    jobQueue = messageWorker.jobQueue()

                ## In case of pdf2image, it has longer result wait time, e.g. 60sec
                elif jobTypeStr == QueueJobType.PDF2IMAGE:
                    resultWaitSec = 60
                    jobType = QueueJobType.PDF2IMAGE

                    ## Find out queue that it is least busy from the workers
                    ## NOTE: queue can be shared by multiple workers
                    jobQueue = QueueWorker.leastBusyWorkers(pdfWorkers).jobQueue()
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

        async def onUploadFile(file: UploadFile, outBaseDir: str, outBaseNameNoExt: str):
            funcName = onUploadFile.__name__
            fileName = file.filename if file.filename is not None else "unknown.dat"
            prefix = f"{funcName}[{file.filename}]"
            try:
                ## Get file extension
                ## Reason to get file ext:
                ## - Try to preserve file ext but discard original filename
                ## - original filename may contain illegal/undesired characters, e.g. spaces and symbols
                fileExt = fileName.split(".")[-1]
                if fileExt == "":
                    raise Exception(f"missing file ext, name={fileName}")

                U.logD(f"{prefix} uploading file...")
                fileData = await file.read()
                U.logD(f"{prefix} fileSize={len(fileData)}")

                ## Write file lambda
                def writeFileTask_() -> str:
                    outFilePath = f"{outBaseDir}/{outBaseNameNoExt}.{fileExt}"
                    with open(f"{outFilePath}", "wb") as f:
                        f.write(fileData)
                    return outFilePath

                ## Run the write file lambda in pool thread
                ## Reason:
                ## - If the write data is large, the write operation may block the main thread
                ## - Running the task in a pool thread to resolve this potential issue
                outFilePath = await asyncio.to_thread(writeFileTask_)
                U.logD(f"{prefix} fileWritten={outFilePath}")

                return outFilePath
            except Exception as e:
                U.throwPrefix(prefix, e)

        ## Use of @dataclass to define form data model
        ## https://stackoverflow.com/questions/60127234/how-to-use-a-pydantic-model-with-form-data-in-fastapi
        @dataclass
        class UploadFormData:
            data: str = Form(...)
            message: str = Form(...)
            files: List[UploadFile] = File(...)

        @api.post("/uploadFiles")
        # async def uploadFiles(formData: UploadFormData = Depends(), files: List[UploadFile] = File(...)):
        async def uploadFiles(formData: UploadFormData = Depends()):
            jobId = U.uuid()
            funcName = uploadFiles.__name__
            prefix = f"{funcName}[{jobId}]"
            try:
                files = formData.files
                U.logD(f"{prefix} form={formData}, nFiles={len(files)}")

                # Create async tasks for file uploads
                baseDir = f"./out/uploads/{jobId}"
                os.makedirs(baseDir)
                fileUploadAsyncTasks = [
                    onUploadFile(file, baseDir, f"file-{fileIdx+1:0>2}") for fileIdx, file in enumerate(files)
                ]

                ## wait for completion of all async tasks
                outFilePaths = await asyncio.gather(*fileUploadAsyncTasks)
                U.logD(f"{prefix} request completed")

                return {
                    "data": {
                        "id": jobId,
                        "result": {
                            "data": formData.data,
                            "message": formData.message,
                            "nFiles": len(files),
                            "outFiles": list(zip([f.filename for f in files], outFilePaths)),
                        },
                    }
                }
            except Exception as e:
                throwHttpPrefix(prefix, jobId, e)

        ## FastAPI instance is returned
        return api
    except Exception as e:
        U.throwPrefix(prefix, e)


api = asyncio.run(initFastApi_())
