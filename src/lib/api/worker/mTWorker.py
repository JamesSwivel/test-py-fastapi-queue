import asyncio
import threading
import time
import queue
import os
from queue import Queue
from enum import Enum
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal, NotRequired, Tuple
import pdf2image
import util as U


class QueueJobType(str, Enum):
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
    workerName: str
    data: str
    dequeueElapsedMs: int
    processElapsedMs: int
    totalElapsedMs: int


class QueueWorkerOpts(TypedDict):
    queueMaxSize: NotRequired[int]
    queue: NotRequired[Optional[queue.Queue]]


class MultiThreadQueueWorker(threading.Thread):
    QUEUE_MAX_SIZE = 10

    @classmethod
    def leastBusyWorkers(cls, workers: List["MultiThreadQueueWorker"]) -> "MultiThreadQueueWorker":
        funcName = cls.leastBusyWorkers.__name__
        prefix = funcName
        try:
            ## Since multiple workers may share a queue, first build this info
            queues: Dict[queue.Queue, List["MultiThreadQueueWorker"]] = {}
            for worker in workers:
                workerQueue = worker.jobQueue()
                if not (workerQueue in queues):
                    queues[workerQueue] = [worker]
                else:
                    queues[workerQueue].append(worker)

            ## debug
            isDebug = True
            if isDebug:
                U.logD(
                    f"{prefix} unique queues={len(queues)}, workers={[ [ w.name() for w in queues[q]]  for q in queues  ]}"
                )

            ## Get size of unique queues
            ## NOTE: If there is running task in the worker, add 1 to the size since it is still running
            queueSizes = [q.qsize() + sum([1 if w.isRunningJob() else 0 for w in queues[q]]) for q in queues]

            ## Find out the work who has the smallest queue size
            queueIdxMinSize = queueSizes.index(min(queueSizes))
            queueMinSize = list(queues.keys())[queueIdxMinSize]
            targetWorker = queues[queueMinSize][0]

            return targetWorker
        except Exception as e:
            U.throwPrefix(prefix, e)

    ## limit the instance variable
    ## Why? avoid bugs some methods created wrong instance variable
    __slots__ = ("workerName_", "jobQueue_", "threadId_", "startedPromise_", "isWorkerStarted_", "isRunningJob_")

    def __init__(self, workerName: str, startedPromise: asyncio.Future[bool], optsIn: Optional[QueueWorkerOpts]):
        funcName = f"{MultiThreadQueueWorker.__name__}.ctor"
        prefix = funcName
        try:
            # U.logD(f"{prefix}")

            ## build default options
            queueMaxSize = (
                optsIn["queueMaxSize"]
                if optsIn is not None and "queueMaxSize" in optsIn
                else MultiThreadQueueWorker.QUEUE_MAX_SIZE
            )
            opts = {
                "queueMaxSize": queueMaxSize,
                "queue": (
                    optsIn["queue"]
                    if optsIn is not None and "queue" in optsIn and optsIn["queue"] is not None
                    else Queue(maxsize=queueMaxSize)
                ),
            }

            ## must call base class ctor
            super().__init__()

            self.workerName_ = workerName
            self.isWorkerStarted_ = False
            self.startedPromise_ = startedPromise

            ## create job queue
            self.jobQueue_: Queue[QueueJob] = opts["queue"]

            ## get thread id (not yet assigned until it is started)
            self.threadId_: int = 0
        except Exception as e:
            U.throwPrefix(prefix, e)

    def name(self):
        return self.workerName_

    def run(self):
        self.worker_()

    def jobQueue(self):
        return self.jobQueue_

    def isJobQueueFull(self):
        return self.jobQueue_.full()

    def isJobQueueEmpty(self):
        return self.jobQueue_.empty()

    def isRunningJob(self):
        return self.isRunningJob_

    def jobQueueMaxSize(self):
        return self.jobQueue_.maxsize

    def worker_(self):
        self.threadId_ = self.ident if self.ident is not None else 0

        funcName = self.worker_.__name__
        prefix = f"{funcName}[{self.threadId_}]"

        ## notify worker is started
        if not self.isWorkerStarted_:
            self.startedPromise_.set_result(True)
            self.isWorkerStarted_ = True
            U.logI(f"{prefix} running... maxQueueSize={self.jobQueue_.maxsize}")

        lastAliveEpms = U.epochMs()
        while True:
            try:
                self.isRunningJob_ = False
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
        prefix = f"{self.workerName_}.{funcName}[{job['id']}]"
        result: QueueJobResult = {
            "errCode": "",
            "err": "",
            "data": "",
            "workerName": self.workerName_,
            "dequeueElapsedMs": 0,
            "processElapsedMs": 0,
            "totalElapsedMs": 0,
        }
        resultPromise: Optional[asyncio.Future["QueueJobResult"]] = None
        try:
            self.isRunningJob_ = True
            U.logW(f"{prefix} {job}")

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
            U.logPrefixE(prefix, e)
            U.throwPrefix(prefix, e)

    def onJobPdf2image(self, jobResult: QueueJobResult, job: QueueJob, jobData: QueueJobPdf2Image):
        funcName = self.onJobPdf2image.__name__
        prefix = funcName
        try:
            pdfPath = jobData["pdfFilePath"]
            pages = pdf2image.convert_from_path(pdfPath, thread_count=4)
            if pages is not None and len(pages) > 0:
                basedDir = f"./out/pdf2image/{job['id']}"
                os.makedirs(basedDir)
                for idx, page in enumerate(pages):
                    page.save(f"{basedDir}/image-{idx:0>2}.png")
            jobResult["data"] = f"job[{jobData['tag']}] finished ({U.epochMs()}), nPages={len(pages)}"
        except Exception as e:
            U.logPrefixE(prefix, e)
            U.throwPrefix(prefix, e)
