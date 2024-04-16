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
    async def initServer(cls):
        funcName = cls.initServer.__name__
        prefix = funcName
        try:

            @asynccontextmanager
            async def lifespan_(application: FastAPI):

                def onSignal_(signalNumber, frame):
                    U.logW(f"{prefix} SIGNAL received, exiting app...")
                    mTWorkers = [cls.messageWorker] + [p for p in cls.pdfWorkers]
                    for w in mTWorkers:
                        w.stop()
                    for w in mTWorkers:
                        w.join()
                    U.logW(f"{prefix} all multi-thread workers stopped")
                    U.logW(f"{prefix} exiting system...")
                    sys.exit()

                signal.signal(signal.SIGINT, onSignal_)
                U.logD(f"{prefix} lifespan.start")
                yield
                U.logD(f"{prefix} lifespan.shutdown")

            ## Create a FastAPI instance
            cls.app = FastAPI(lifespan=lifespan_)

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
            # cls.mpManager = MultiProcessManager("mpMgr")
            # for i in range(8):
            #     cls.mpManager.startProcess(f"pdfWorker{i+1}")

            ## init all endpoints
            initAllEndpoints(cls.app)

            ## FastAPI instance is returned
            return cls.app
        except Exception as e:
            U.throwPrefix(prefix, e)
