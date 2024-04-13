import os
import time
import queue
from threading import Thread
import multiprocessing
from multiprocessing import Process, Manager
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal, NotRequired, Tuple
import pdf2image

import util as U


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
    __slots__ = ("name", "jobQueue_", "resultQueue_", "resultThread_", "processes_")

    def __init__(self, name: str, jobQueueMaxSize=JOB_QUEUE_MAX_SIZE, resultQueueMaxsize=RESULT_QUEUE_MAX_SIZE):
        funcName = f"{MultiProcessManager.__name__}.ctor"
        prefix = funcName
        try:
            self.name = name

            ## NOTE: All processes shared the single job queue and result queue
            self.jobQueue_: multiprocessing.Queue = multiprocessing.Queue(maxsize=jobQueueMaxSize)
            self.resultQueue_: multiprocessing.Queue = multiprocessing.Queue(maxsize=resultQueueMaxsize)

            ## Single thread worker to process result from all processes
            self.resultThread_: Thread = Thread(target=self.resultQueueThreadWorker_)
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

    def resultQueueThreadWorker_(self):
        funcName = self.resultQueueThreadWorker_.__name__
        prefix = f"MpMgr[{self.name}][{funcName}]"
        try:
            U.logD(f"{prefix} running...")
            while True:
                job = self.resultQueue_.get()
                U.logD(f"{prefix} job={job}")
        except Exception as e:
            U.logPrefixE(prefix, e)

    def startProcess(self, workerName: str):
        funcName = self.startProcess.__name__
        prefix = funcName
        try:
            if workerName in self.processes_:
                raise Exception(f"processes[{workerName}] already exist")
            workerProcess = Process(
                target=MultiProcessManager.processWorker_, args=(workerName, self.jobQueue_, self.resultQueue_)
            )
            self.processes_[workerName] = {"process": workerProcess}
            workerProcess.start()
        except Exception as e:
            U.throwPrefix(prefix, e)

    @classmethod
    def processWorker_(cls, workerName: str, jobQueue: multiprocessing.Queue, resultQueue: multiprocessing.Queue):
        """
        WARNING:
        - This function runs in separated process
        - The variables accessed here is different from what in the main thread
        """
        funcName = cls.processWorker_.__name__
        prefix = f"Mp[{workerName}][{os.getpid()}]"
        try:
            U.logD(f"{prefix} running...")
            while True:
                job = jobQueue.get()
                U.logD(f"{prefix} job={job}")
                cls.onJobPdf2image()
                continue
        except Exception as e:
            U.throwPrefix(prefix, e)

    @classmethod
    def onJobPdf2image(cls):
        jobId = U.uuid()
        funcName = cls.onJobPdf2image.__name__
        prefix = f"{funcName}[{jobId}]"
        try:
            onProcessEpms = U.epochMs()
            U.logD(f"{prefix} starts...")
            pdfPath = "data/regal-17pages.pdf"
            pages = pdf2image.convert_from_path(pdfPath, thread_count=4)
            if pages is not None and len(pages) > 0:
                basedDir = f"./out/pdf2image/{jobId}"
                os.makedirs(basedDir)
                for idx, page in enumerate(pages):
                    page.save(f"{basedDir}/image-{idx:0>2}.png")
            onResultEpms = U.epochMs()
            processElapsedMs = onResultEpms - onProcessEpms
            U.logD(f"{prefix} done, elapsedMs={processElapsedMs}")
        except Exception as e:
            U.logPrefixE(prefix, e)
            U.throwPrefix(prefix, e)
