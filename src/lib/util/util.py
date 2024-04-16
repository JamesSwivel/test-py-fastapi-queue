import sys
import time
import uuid as PyUuid_
from typing import Union, Dict, TypedDict


def pythonVer():
    """
    Get Python version dict
    """

    class Returns_pythonVer(TypedDict):
        major: int
        minor: int
        micro: int
        verStr: str
        verInt: int

    ver = sys.version_info
    out: Returns_pythonVer = {
        "major": ver.major,
        "minor": ver.minor,
        "micro": ver.micro,
        "verStr": f"{ver.major}.{ver.minor}.{ver.micro}",
        "verInt": int(ver.major * 1e8 + ver.minor * 1e4 + ver.micro),
    }
    return out


def epochMs():
    return int(time.time() * 1000)


def epochSec():
    return int(time.time())


def uuid():
    return str(PyUuid_.uuid4())


def isUuid(s: str) -> bool:
    """
    UUid?
      e.g. lex=36
                1         2         3
      012345678901234567890123456789012345
      d33c425f-64c0-4d50-afe4-6eb5739a056b
    """
    if len(s) != 36:
        return False
    ## check presence of "-"
    for idx in [8, 13, 18, 23]:
        if s[idx] != "-":
            return False

    ## must be 5 segments
    splits = s.split("-")
    if len(splits) != 5:
        return False

    ## when joined, it must be hex str
    return isHexStr("".join(splits))


def isHexStr(s: str) -> bool:
    if len(s) % 2 != 0:
        return False
    return all(c in "01234567890abcdef" for c in s)
