import os
import sys
import datetime
from typing import Union, NoReturn, TypedDict, Literal, overload
from .log import logI, logD, logW, logE, logPrefixE, throwPrefix


def isFileExist(p: str) -> bool:
    return os.path.exists(p) and os.path.isfile(p)


def isDirExist(p: str) -> bool:
    return os.path.exists(p) and os.path.isdir(p)


def parseFilePath(filePath: str):
    """'
    Parse file path

    Returns:
        (baseDir, baseName, ext, baseNameNoExt) e.g. /aa/bb/cc/dd.txt -> (/aa/bb/cc, dd.txt, .txt, dd)
    """

    class TReturns_parseFilePath(TypedDict):
        baseDir: str
        baseName: str
        ext: str
        baseNameNoExt: str

    ## Get base dir
    baseDir = os.path.dirname(filePath)
    if baseDir == "":
        baseDir = "./"

    ## Get basename
    ## NOTE: basename(f) return only basename, not including dir
    baseName = os.path.basename(filePath)

    ## NOTE:
    ## - splitext(f) returns a tuple
    ## - First item: basedir/basename with extension removed, e.g. '/aa/bb/cc.txt' -> 'aa/bb/cc',
    ## - Second item: extension with leading ., e.g. .mp4. It returns "" if input f has no extension
    _, ext = os.path.splitext(filePath)

    ## get basename without ext
    ## e.g. aaa.bbb.ext -> aaa.bbb, aaa.mp4 -> aaa, bbb -> bbb
    baseNameNoExt = baseName[0:len(baseName)- len(ext)]

    out: TReturns_parseFilePath = {"baseDir": baseDir, "baseName": baseName, "ext": ext, "baseNameNoExt": baseNameNoExt}
    return out


def replaceFileExt(f: str, newExt: str):
    """
    Replace file extension

    Args:
        f: full filepath, e.g. /aa/bb/cc/xx.jpg
        newExt: new extension to replace, e.g. .mp4

    Returns:
        e.g. /aa/bb/cc/xx.jpg -> /aa/bb/cc/xx.mp4
    """
    baseNameWithDir, _ = os.path.splitext(f)
    newFilename = f"{baseNameWithDir}{newExt}"
    return newFilename


# @overload
# def chCwd(dirPath: str):
#     """
#     change CWD
#     """


# @overload
# def chCwd(dirPath: str, isThrow: bool) -> NoReturn:
#     """
#     Change CWD. Throw if error
#     """


def chCwd(dirPath: str, isThrow: bool = False):
    """
    Change cwd according to filePath.
    Mostly used when filePath is the main script filePath

    Args:
        dirPath: dir path
        isThrow: true=throw if error (default is False)

    Returns:
        true=success
    """
    funcName = chCwd.__name__
    prefix = funcName
    isOk = False
    try:
        os.chdir(dirPath)
        logI(f"cwd={os.getcwd()}")
        isOk = True
    except Exception as e:
        if isThrow:
            throwPrefix(prefix, f"failed to chCwd={dirPath}, e={e}")
        logPrefixE(prefix, e)
    return isOk


# @overload
# def chCwdFromFilePath(filePath: str):
#     """
#     change CWD given a filePath, e.g. script main filePath
#     """


# @overload
# def chCwdFromFilePath(filePath: str, isThrow: bool) -> NoReturn:
#     """
#     change CWD given a filePath, e.g. script main filePath.
#     Throw exception if error
#     """


def chCwdFromFilePath(filePath: str, isThrow: bool = False):
    """
    Change cwd according to filePath.
    Mostly used when filePath is the main script filePath

    Args:
        filePath: file path
        isThrow: true=throw if error (default is False)

    Returns:
        true=success
    """
    funcName = chCwdFromFilePath.__name__
    prefix = funcName
    isOk = False
    try:
        baseDir = parseFilePath(filePath)["baseDir"]
        chCwd(baseDir, True)  ## True=isThrow
        isOk = True
    except Exception as e:
        if isThrow:
            throwPrefix(prefix, e)
        logPrefixE(funcName, e)
    return isOk
