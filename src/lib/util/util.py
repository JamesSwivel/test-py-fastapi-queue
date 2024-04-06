import sys
import time
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
