import asyncio
import threading
import time
import queue
import os
import random
from queue import Queue
from enum import Enum
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal
import pdf2image
import util as U


class QueueJobType(str, Enum):
    MESSAGE = "message"
    PDF2IMAGE = "pdf2image"


class QueueJobResult(TypedDict):
    errCode: str
    err: str
    workerName: str
    data: str
    dequeueElapsedMs: int
    processElapsedMs: int
    totalElapsedMs: int


class QueueJobBase(TypedDict):
    createEpms: int
    id: str
    promise: asyncio.Future["QueueJobResult"]


class QueueJobMessage(QueueJobBase):
    randomNo: int
    message: str


class QueueJobPdf2Image(QueueJobBase):
    pdfFilePath: str


class Test:
    ## limit the instance variable
    ## Why? avoid bugs some methods created wrong instance variable
    __slots__ = ("var1_", "var2_")

    def __init__(self):
        pass

    def createJobMessage(self) -> QueueJobMessage:
        funcName = self.createJobMessage.__name__
        prefix = funcName
        try:
            job: QueueJobMessage = {
                ## inherited properties
                "createEpms": U.epochSec(),
                "id": U.uuid(),
                "promise": asyncio.Future(),
                ## addon properties
                "message": "hello world",
                "randomNo": random.randint(1, 10),
            }
            return job
        except Exception as e:
            U.throwPrefix(prefix, e)

    def createJobPdf2Image(self) -> QueueJobPdf2Image:
        funcName = self.createJobPdf2Image.__name__
        prefix = funcName
        try:
            job: QueueJobPdf2Image = {
                ## inherited properties
                "createEpms": U.epochSec(),
                "id": U.uuid(),
                "promise": asyncio.Future(),
                ## addon properties
                "pdfFilePath": f"./data/regal-17pages.pdf",
            }
            return job
        except Exception as e:
            U.throwPrefix(prefix, e)

    def testCreateJobs(self):
        funcName = self.testCreateJobs.__name__
        prefix = funcName
        try:
            jobMessage = self.createJobMessage()
            jobPdf2image = self.createJobPdf2Image()
        except Exception as e:
            U.throwPrefix(prefix, e)
