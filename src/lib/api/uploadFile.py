import os
import asyncio
from dataclasses import dataclass
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any, NoReturn, Annotated
from fastapi import FastAPI, Body, HTTPException, File, UploadFile, Form, Depends

import util as U
from util.fastApi import throwHttpPrefix


def initEndpoints(app: FastAPI):
    U.logD(f"{initEndpoints.__name__}[{__file__.split('/')[-1]}] loading...")

    ## Use of @dataclass to define form data model
    ## https://stackoverflow.com/questions/60127234/how-to-use-a-pydantic-model-with-form-data-in-fastapi
    @dataclass
    class UploadFormData:
        data: str = Form(...)
        message: str = Form(...)
        files: List[UploadFile] = File(...)

    async def onUploadFile(file: UploadFile, outBaseDir: str, outBaseNameNoExt: str):
        funcName = onUploadFile.__name__
        fileName = file.filename if file.filename is not None else "unknown.dat"
        prefix = f"{funcName}[{file.filename}]"
        try:
            ## Get file extension
            ## Reason to get file ext:
            ## - Try to preserve file ext but discard original filename
            ## - original filename may contain illegal/undesired characters, e.g. spaces and symbols
            fileExt = fileName.split(".")[-1]
            if fileExt == "":
                raise Exception(f"missing file ext, name={fileName}")

            U.logD(f"{prefix} uploading file...")
            fileData = await file.read()
            U.logD(f"{prefix} fileSize={len(fileData)}")

            ## Write file lambda
            def writeFileTask_() -> str:
                outFilePath = f"{outBaseDir}/{outBaseNameNoExt}.{fileExt}"
                with open(f"{outFilePath}", "wb") as f:
                    f.write(fileData)
                return outFilePath

            ## Run the write file lambda in pool thread
            ## Reason:
            ## - If the write data is large, the write operation may block the main thread
            ## - Running the task in a pool thread to resolve this potential issue
            outFilePath = await asyncio.to_thread(writeFileTask_)
            U.logD(f"{prefix} fileWritten={outFilePath}")

            return outFilePath
        except Exception as e:
            U.throwPrefix(prefix, e)

    @app.post("/uploadFiles")
    # async def uploadFiles(formData: UploadFormData = Depends(), files: List[UploadFile] = File(...)):
    async def uploadFiles(formData: UploadFormData = Depends()):
        jobId = U.uuid()
        funcName = uploadFiles.__name__
        prefix = f"{funcName}[{jobId}]"
        try:
            files = formData.files
            U.logD(f"{prefix} form={formData}, nFiles={len(files)}")

            # Create async tasks for file uploads
            baseDir = f"./out/uploads/{jobId}"
            os.makedirs(baseDir)
            fileUploadAsyncTasks = [
                onUploadFile(file, baseDir, f"file-{fileIdx+1:0>2}") for fileIdx, file in enumerate(files)
            ]

            ## wait for completion of all async tasks
            outFilePaths = await asyncio.gather(*fileUploadAsyncTasks)
            U.logD(f"{prefix} request completed")

            return {
                "data": {
                    "id": jobId,
                    "result": {
                        "data": formData.data,
                        "message": formData.message,
                        "nFiles": len(files),
                        "outFiles": list(zip([f.filename for f in files], outFilePaths)),
                    },
                }
            }
        except Exception as e:
            throwHttpPrefix(prefix, e, jobId)
