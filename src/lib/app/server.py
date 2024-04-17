import sys
import os
import asyncio
import queue
import signal
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn, Annotated

import util as U
from api.worker import MultiThreadQueueWorker, MultiProcessManager
from api import initAllEndpoints


class FastApiServer:
    MESSAGE_WORKER_MAX_QSIZE = 10
    PDF_WORKER_MAX_QSIZE = 10
    PDF_WORKER_COUNT = 8
    IS_PDF_WORKER_SINGLE_QUEUE = True

    app: FastAPI
    messageWorker: MultiThreadQueueWorker
    pdfWorkers: List[MultiThreadQueueWorker]
    mpManager: MultiProcessManager

    @classmethod
    def stopAllThreadWorkers(cls):
        funcName = cls.stopAllThreadWorkers.__name__
        prefix = funcName
        try:
            U.logW(f"{prefix} stopping all multi-thread Workers...")
            mTWorkers = [cls.messageWorker] + [p for p in cls.pdfWorkers]
            for w in mTWorkers:
                w.stop()
            for w in mTWorkers:
                w.join()
            U.logW(f"{prefix} all multi-thread workers stopped")
        except Exception as e:
            U.logPrefixE(prefix, e)

    @classmethod
    def stopAllProcessWorkers(cls):
        funcName = cls.stopAllProcessWorkers.__name__
        prefix = funcName
        try:
            cls.mpManager.stopAllProcesses()
        except Exception as e:
            U.logPrefixE(prefix, e)

    @classmethod
    @asynccontextmanager
    async def fastApiLifeSpan(cls, application: FastAPI):
        funcName = cls.fastApiLifeSpan.__name__
        prefix = funcName
        try:
            U.logW(f"{prefix} >>>>>>> onStart")
            yield
            U.logW(f"{prefix} >>>>>>> onShutdown")
            cls.stopAllProcessWorkers()
            cls.stopAllThreadWorkers()

            ## important note:
            ## https://github.com/simonw/datasette-scale-to-zero/issues/2
            ## - normal exit causes a lot of strange error messages
            ## - sys.exit(0) also has the same issue
            ## - calling os._exit(0) will ignore the error messages since it will NOT call handlers on exit
            os._exit(0)
        except Exception as e:
            U.logPrefixE(prefix, e)

    @classmethod
    async def initServer(cls):
        funcName = cls.initServer.__name__
        prefix = funcName
        try:

            ## Create a FastAPI instance
            cls.app = FastAPI(lifespan=cls.fastApiLifeSpan)

            ## Start a message worker in separated thread
            messageWorkerStartPromise = asyncio.Future()
            cls.messageWorker = MultiThreadQueueWorker(
                "messageWorker", messageWorkerStartPromise, {"queueMaxSize": cls.MESSAGE_WORKER_MAX_QSIZE}
            )
            cls.messageWorker.start()

            ## Start a pool of pdf workers, each running in its own thread
            if cls.IS_PDF_WORKER_SINGLE_QUEUE:
                U.logW(f"Use single queue for pdf worker!")
                pdfWorkerSingleQueue = queue.Queue()
            pdfWorkerStartPromises = [asyncio.Future() for i in range(cls.PDF_WORKER_COUNT)]
            cls.pdfWorkers = [
                MultiThreadQueueWorker(
                    f"pdfWorker{i+1}",
                    pdfWorkerStartPromises[i],
                    {
                        "queueMaxSize": cls.PDF_WORKER_MAX_QSIZE,
                        "queue": pdfWorkerSingleQueue if cls.IS_PDF_WORKER_SINGLE_QUEUE else None,
                    },
                )
                for i in range(cls.PDF_WORKER_COUNT)
            ]
            for i in range(cls.PDF_WORKER_COUNT):
                cls.pdfWorkers[i].start()

            ## await until workers are running
            await messageWorkerStartPromise
            for i in range(cls.PDF_WORKER_COUNT):
                await pdfWorkerStartPromises[i]

            ## Start a pool of multi-process pdf2image workers
            cls.mpManager = MultiProcessManager("mpMgr")
            for i in range(8):
                cls.mpManager.startProcess(f"pdfWorker{i+1}")

            ## init all endpoints
            initAllEndpoints(cls.app)

            ## FastAPI instance is returned
            return cls.app
        except Exception as e:
            U.throwPrefix(prefix, e)
