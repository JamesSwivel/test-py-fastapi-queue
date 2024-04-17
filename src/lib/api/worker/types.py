import asyncio
from enum import Enum
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, Optional, Literal, NotRequired, Tuple


class QueueJobType(str, Enum):
    EVENT = "event"
    MESSAGE = "message"
    PDF2IMAGE = "pdf2image"


class QueueEventType(str, Enum):
    STOP = "stop"


class QueueJobEvent(TypedDict):
    tag: Literal[QueueJobType.EVENT]
    action: QueueEventType


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
    jobData: Union[QueueJobMessage, QueueJobPdf2Image, QueueJobEvent]
    promise: asyncio.Future["QueueJobResult"]


class MpQueueJob(TypedDict):
    createEpms: int
    id: str
    jobType: QueueJobType
    jobData: Union[QueueJobMessage, QueueJobPdf2Image, QueueJobEvent]
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
