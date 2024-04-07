import asyncio
import threading
import time
import queue
from queue import Queue
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional
import util as U


class QueueJob(TypedDict):
    createEpms: int
    id: str
    randomNo: int
    message: str
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
    __slots__ = ("jobQueue_", "threadId_", "startedPromise_", "isWorkerStarted_")

    def __init__(self, startedPromise: asyncio.Future[bool], maxSize=QUEUE_MAX_SIZE):
        funcName = f"{QueueWorker.__name__}.ctor"
        prefix = funcName
        try:
            U.logD(f"{prefix}")

            ## must call base class ctor
            super().__init__()

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
        prefix = f"{funcName}[{self.threadId_}]"

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

            ## Simulate CPU intensive task
            onProcessEpms = U.epochMs()
            if job["randomNo"] >= 8:
                U.logW(f"{prefix} simulating a CPU intensive task that runs for an unexpected long time! (10secs)")
                time.sleep(10)
            else:
                time.sleep(3)
            onResultEpms = U.epochMs()

            ## fill in the result
            result["processElapsedMs"] = onResultEpms - onProcessEpms
            result["totalElapsedMs"] = onResultEpms - job["createEpms"]
            result["data"] = f"job finished ({U.epochMs()})"

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
