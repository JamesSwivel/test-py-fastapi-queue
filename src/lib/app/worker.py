import asyncio
import threading
import time
import queue
from queue import Queue
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any
import util as U


class QueueItem(TypedDict):
    id: str
    message: str
    promise: asyncio.Future[str]


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
            self.jobQueue_: Queue[QueueItem] = Queue(maxsize=QueueWorker.QUEUE_MAX_SIZE)

            ## get thread id
            threadId = threading.current_thread().ident
            self.threadId_: int = threadId if threadId is not None else 0
        except Exception as e:
            U.throwPrefix(prefix, e)

    def run(self):
        self.worker_()

    def jobQueue(self):
        return self.jobQueue_

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
                if nowEpms - lastAliveEpms >= 5 * 60 * 1000:
                    U.logD(f"{prefix} alive...")
                    lastAliveEpms = nowEpms

                try:
                    ## Get the job item from the queue
                    qItem = self.jobQueue_.get(timeout=5)
                except queue.Empty:
                    # U.logD(f"queue is empty")
                    continue

                ## process the queue item
                self.onQueueItem(qItem)

                ## it is to emulate CPU intensive task
                time.sleep(3)

            except Exception as e:
                U.logPrefixE(prefix, e)

    def onQueueItem(self, item: QueueItem):
        funcName = self.onQueueItem.__name__
        prefix = funcName
        try:
            nowEpms = U.epochMs()
            U.logD(f"{prefix} {item}")
            item["promise"].set_result(f"done at {nowEpms}")
        except Exception as e:
            U.throwPrefix(prefix, e)
