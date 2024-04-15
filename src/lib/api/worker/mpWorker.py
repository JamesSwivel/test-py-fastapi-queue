import os
import asyncio
import queue
import threading
import multiprocessing
from multiprocessing import Process, Manager
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal, NotRequired, Tuple
import pdf2image

import util as U
from .types import MpQueueJob, QueueJob, QueueJobMessage, QueueJobPdf2Image, QueueJobResult, QueueJobType


class MPQueueJobResult(TypedDict):
    errCode: str
    err: str
    workerName: str
    data: str
    dequeueElapsedMs: int
    processElapsedMs: int
    totalElapsedMs: int


class MultiProcessManager:
    JOB_QUEUE_MAX_SIZE = 10
    RESULT_QUEUE_MAX_SIZE = 10

    ## limit the instance variable
    ## Why? avoid bugs some methods created wrong instance variable
    __slots__ = (
        "name",
        "jobQueue_",
        "resultQueue_",
        "resultThread_",
        "processes_",
        "resultPromises_",
        "resultPromisesLock_",
    )

    def __init__(self, name: str, jobQueueMaxSize=JOB_QUEUE_MAX_SIZE, resultQueueMaxsize=RESULT_QUEUE_MAX_SIZE):
        funcName = f"{MultiProcessManager.__name__}.ctor"
        prefix = funcName
        try:
            self.name = name

            ## NOTE: All processes shared the single job queue and result queue
            self.jobQueue_: multiprocessing.Queue[MpQueueJob] = multiprocessing.Queue(maxsize=jobQueueMaxSize)
            self.resultQueue_: multiprocessing.Queue[Tuple[str, QueueJobResult]] = multiprocessing.Queue(
                maxsize=resultQueueMaxsize
            )

            ## Single thread worker to process result from all processes
            self.resultPromises_: Dict[str, asyncio.Future["QueueJobResult"]] = {}
            self.resultPromisesLock_ = threading.Lock()
            self.resultThread_: threading.Thread = threading.Thread(target=self.resultQueueThreadWorker_)
            self.resultThread_.start()

            ## All processes info
            class MultiProcessWorker(TypedDict):
                process: Process

            self.processes_: Dict[str, MultiProcessWorker] = {}

        except Exception as e:
            U.throwPrefix(prefix, e)

    def jobQueue(self):
        return self.jobQueue_

    def resultQueue(self):
        return self.resultQueue_

    def enqueue(self, job: QueueJob):
        funcName = self.enqueue.__name__
        prefix = f"{funcName}[{job['id']}]"
        try:
            with self.resultPromisesLock_:
                ## jobId must not exist in the result promises
                jobId = job["id"]
                if jobId in self.resultPromises_:
                    raise Exception(f"jobId found in resultPromises_")

                ## Convert QueueJob to MpQueueJob
                ## Reason: Future variable cannot be passed cross processes
                mpJob: MpQueueJob = {
                    "createEpms": job["createEpms"],
                    "id": jobId,
                    "jobData": job["jobData"],
                    "jobType": job["jobType"],
                    "promise": job["id"],
                }
                self.jobQueue_.put(mpJob, block=False)

                ## Keep the result promise
                self.resultPromises_[jobId] = job["promise"]

                ## housekeeping: All done promises should be clear
                promiseIdsToBeRemoved: List[str] = []
                for k, v in self.resultPromises_.items():
                    if v.done():
                        promiseIdsToBeRemoved.append(k)
                if len(promiseIdsToBeRemoved) > 0:
                    for promiseId in promiseIdsToBeRemoved:
                        del self.resultPromises_[promiseId]
                        U.logD(f"resultPromises[{promiseId}] removed")

        except Exception as e:
            U.throwPrefix(prefix, e)

    def resultQueueThreadWorker_(self):
        funcName = self.resultQueueThreadWorker_.__name__
        prefix = f"MpMgr[{self.name}][{funcName}]"
        try:
            U.logD(f"{prefix} running...")
            while True:
                promiseId, result = self.resultQueue_.get()
                U.logD(f"{prefix} promiseId={promiseId}, result={result}")

                with self.resultPromisesLock_:
                    if not (promiseId in self.resultPromises_):
                        raise Exception(f"promiseId not found in resultPromises")
                    promise = self.resultPromises_[promiseId]
                    if not promise.done():
                        self.resultPromises_[promiseId].set_result(result)
                    else:
                        U.logD(f"{prefix} job already done, promiseId={promiseId}")
                    del self.resultPromises_[promiseId]

        except Exception as e:
            U.logPrefixE(prefix, e)

    def startProcess(self, workerName: str):
        funcName = self.startProcess.__name__
        prefix = funcName
        try:
            if workerName in self.processes_:
                raise Exception(f"processes[{workerName}] already exist")
            worker = MultiProcessWorker(self, workerName, self.jobQueue_, self.resultQueue_)
            workerProcess = Process(target=worker.worker)
            self.processes_[workerName] = {"process": workerProcess}
            workerProcess.start()
        except Exception as e:
            U.throwPrefix(prefix, e)


class MultiProcessWorker:

    ## limit the instance variable
    ## Why? avoid bugs some methods created wrong instance variable
    __slots__ = ("workerName_", "mpMgr_", "pid", "jobQueue_", "resultQueue_", "prefix_", "isRunningJob_")

    def __init__(
        self,
        mpMgr: MultiProcessManager,
        workerName: str,
        jobQueue: multiprocessing.Queue,
        resultQueue: multiprocessing.Queue,
    ):
        funcName = f"{MultiProcessWorker.__name__}.ctor"
        prefix = funcName
        try:
            self.mpMgr_ = mpMgr
            self.workerName_ = workerName
            self.pid = os.getpid()
            self.jobQueue_: multiprocessing.Queue[MpQueueJob] = jobQueue
            self.resultQueue_: multiprocessing.Queue[Tuple[str, QueueJobResult]] = resultQueue
            self.prefix_ = f"mp[{mpMgr.name}][{workerName}]"
        except Exception as e:
            U.throwPrefix(prefix, e)

    def worker(self):
        funcName = self.worker.__name__
        prefix = f"{self.prefix_}[{os.getpid()}]"
        try:
            U.logD(f"{prefix} running...")
            lastAliveEpms = U.epochMs()
            while True:
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

                continue
        except Exception as e:
            U.throwPrefix(prefix, e)

    def onQueueJob_(self, job: MpQueueJob):
        funcName = self.onQueueJob_.__name__
        prefix = f"{self.prefix_}.{funcName}.job[{job['id']}]"
        result: QueueJobResult = {
            "errCode": "",
            "err": "",
            "data": "",
            "workerName": self.workerName_,
            "dequeueElapsedMs": 0,
            "processElapsedMs": 0,
            "totalElapsedMs": 0,
        }
        resultPromiseId = ""
        try:
            self.isRunningJob_ = True
            U.logW(f"{prefix} {job}")

            resultPromiseId = job["promise"]

            ## calculate elapsed time for job dequeue
            onDequeueEpms = U.epochMs()
            result["dequeueElapsedMs"] = onDequeueEpms - job["createEpms"]

            ## Process CPU intensive task
            onProcessEpms = U.epochMs()
            jobType = job["jobType"]

            ## Convert pdf to image
            if jobType == QueueJobType.PDF2IMAGE and job["jobData"]["tag"] == QueueJobType.PDF2IMAGE:
                self.onJobPdf2image(result, job, job["jobData"])
            else:
                raise Exception(f"invalid jobType")
            onResultEpms = U.epochMs()

            ## fill in the result
            result["processElapsedMs"] = onResultEpms - onProcessEpms
            result["totalElapsedMs"] = onResultEpms - job["createEpms"]

        ## In case of exception, fill in err/errcode to the result
        except Exception as e:
            if resultPromiseId is not None:
                result["errCode"] = "err"
                result["err"] = "error processing job request"

        ## Regardless of exception, it needs to set_result() to notify the original job dispatcher
        finally:
            try:
                if resultPromiseId != "":
                    ## Put the resultPromiseId and the result to result queue (the thread worker)
                    self.resultQueue_.put((resultPromiseId, result))
                else:
                    raise Exception(f"resultPromiseId is empty")
            except Exception as e2:
                U.throwPrefix(prefix, f"failed setting result, err={e2}")

            if result["errCode"] != "":
                U.throwPrefix(prefix, result["err"])

    def onJobPdf2image(self, jobResult: QueueJobResult, job: MpQueueJob, jobData: QueueJobPdf2Image):
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
