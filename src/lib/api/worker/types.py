import asyncio
from enum import Enum
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal, NotRequired, Tuple


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


class MpQueueJob(TypedDict):
    createEpms: int
    id: str
    jobType: QueueJobType
    jobData: Union[QueueJobMessage, QueueJobPdf2Image]
    ## An string id to represent a promise
    promise: str


class QueueJobResult(TypedDict):
    errCode: str
    err: str
    workerName: str
    data: str
    dequeueElapsedMs: int
    processElapsedMs: int
    totalElapsedMs: int
