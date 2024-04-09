import asyncio
import threading
import time
import queue
from queue import Queue
from enum import Enum
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal
import pdf2image
import util as U


class QueueJobType(Enum):
    MESSAGE = "message"
    PDF2IMAGE = "pdf2image"


class QueueJobMessage(TypedDict):
    tag: Literal[QueueJobType.MESSAGE]
    randomNo: int
    message: str


class QueueJobPdf2Image(TypedDict):
    tag: Literal[QueueJobType.PDF2IMAGE]
    pdfFilePath: str


class QueueJob(TypedDict):
    createEpms: int
    id: str
    jobType: QueueJobType
    jobData: Union[QueueJobMessage, QueueJobPdf2Image]
    promise: asyncio.Future["QueueJobResult"]


class QueueJobResult(TypedDict):
    errCode: str
    err: str
    data: str
    dequeueElapsedMs: int
    processElapsedMs: int
    totalElapsedMs: int


class QueueWorker(threading.Thread):
    QUEUE_MAX_SIZE = 10

    ## limit the instance variable
    ## Why? avoid bugs some methods created wrong instance variable
    __slots__ = ("workerName_", "jobQueue_", "threadId_", "startedPromise_", "isWorkerStarted_")

    def __init__(self, workerName: str, startedPromise: asyncio.Future[bool], maxSize=QUEUE_MAX_SIZE):
        funcName = f"{QueueWorker.__name__}.ctor"
        prefix = funcName
        try:
            U.logD(f"{prefix}")

            ## must call base class ctor
            super().__init__()

            self.workerName_ = workerName
            self.isWorkerStarted_ = False
            self.startedPromise_ = startedPromise

            ## create job queue
            self.jobQueue_: Queue[QueueJob] = Queue(maxsize=QueueWorker.QUEUE_MAX_SIZE)

            ## get thread id
            threadId = threading.current_thread().ident
            self.threadId_: int = threadId if threadId is not None else 0
        except Exception as e:
            U.throwPrefix(prefix, e)

    def run(self):
        self.worker_()

    def jobQueue(self):
        return self.jobQueue_

    def isJobQueueFull(self):
        return self.jobQueue_.full()

    def isJobQueueEmpty(self):
        return self.jobQueue_.empty()

    def jobQueueMaxSize(self):
        return self.jobQueue_.maxsize

    def worker_(self):
        funcName = self.worker_.__name__
        prefix = f"{self.workerName_}[{self.threadId_}]"

        ## notify worker is started
        if not self.isWorkerStarted_:
            self.startedPromise_.set_result(True)
            self.isWorkerStarted_ = True
            U.logI(f"{prefix} running...")

        lastAliveEpms = U.epochMs()
        while True:
            try:
                nowEpms = U.epochMs()

                ## Print alive message every 5mins
                if nowEpms - lastAliveEpms >= 5 * 60 * 1000:
                    U.logD(f"{prefix} alive...")
                    lastAliveEpms = nowEpms

                try:
                    ## Get the job item from the queue
                    job = self.jobQueue_.get(timeout=5)
                except queue.Empty:
                    # U.logD(f"queue is empty")

                    ## continue the while loop if job queue is empty
                    continue

                ## process the queue job
                self.onQueueJob_(job)

            except Exception as e:
                U.logPrefixE(prefix, e)

    def onQueueJob_(self, job: QueueJob):
        funcName = self.onQueueJob_.__name__
        prefix = f"{funcName}[{job['id']}]"
        result: QueueJobResult = {
            "errCode": "",
            "err": "",
            "data": "",
            "dequeueElapsedMs": 0,
            "processElapsedMs": 0,
            "totalElapsedMs": 0,
        }
        resultPromise: Optional[asyncio.Future["QueueJobResult"]] = None
        try:
            U.logD(f"{prefix} {job}")

            ## result promise needs to obtain earlier.
            ## In case of exception, it will be used to return errcode/err
            resultPromise = job["promise"]
            if resultPromise.done():
                U.logD(f"{prefix} no need to process job (already canceled)")
                return

            ## calculate elapsed time for job dequeue
            onDequeueEpms = U.epochMs()
            result["dequeueElapsedMs"] = onDequeueEpms - job["createEpms"]

            ## Process CPU intensive task
            onProcessEpms = U.epochMs()
            jobType = job["jobType"]

            ## Simulate CPU task that may run 3 to 10 secs
            ## If randomNo >=8, it runs for longer 10 secs
            if jobType == QueueJobType.MESSAGE and job["jobData"]["tag"] == QueueJobType.MESSAGE:
                self.onJobMessage(result, job, job["jobData"])

            ## Convert pdf to image
            elif jobType == QueueJobType.PDF2IMAGE and job["jobData"]["tag"] == QueueJobType.PDF2IMAGE:
                self.onJobPdf2image(result, job, job["jobData"])
            onResultEpms = U.epochMs()

            ## fill in the result
            result["processElapsedMs"] = onResultEpms - onProcessEpms
            result["totalElapsedMs"] = onResultEpms - job["createEpms"]

        ## In case of exception, fill in err/errcode to the result
        except Exception as e:
            if resultPromise is not None:
                result["errCode"] = "err"
                result["err"] = "error processing job request"

        ## Regardless of exception, it needs to set_result() to notify the original job dispatcher
        finally:
            try:
                if resultPromise is not None:
                    if not resultPromise.done():
                        resultPromise.set_result(result)
                    else:
                        U.logD(f"{prefix} promise already done, state={resultPromise._state}")
                else:
                    raise Exception(f"resultPromise is null")
            except Exception as e2:
                U.throwPrefix(prefix, f"failed setting result, err={e2}")

            if result["errCode"] != "":
                U.throwPrefix(prefix, result["err"])

    def onJobMessage(self, jobResult: QueueJobResult, job: QueueJob, jobData: QueueJobMessage):
        funcName = self.onJobMessage.__name__
        prefix = funcName
        try:
            if jobData["randomNo"] >= 8:
                U.logW(f"{prefix} simulating a CPU intensive task that runs for an unexpected long time! (10secs)")
                time.sleep(10)
            else:
                time.sleep(3)
            jobResult["data"] = f"message job finished ({U.epochMs()})"
        except Exception as e:
            U.throwPrefix(prefix, e)

    def onJobPdf2image(self, jobResult: QueueJobResult, job: QueueJob, jobData: QueueJobPdf2Image):
        funcName = self.onJobPdf2image.__name__
        prefix = funcName
        try:
            pdfPath = jobData["pdfFilePath"]
            pages = pdf2image.convert_from_path(pdfPath)
            if pages is not None and len(pages) > 0:
                for idx, page in enumerate(pages):
                    page.save(f"./out/image-{idx:0>2}.png")
            jobResult["data"] = f"job[{jobData['tag']}] finished ({U.epochMs()}), nPages={len(pages)}"
        except Exception as e:
            U.throwPrefix(prefix, e)
