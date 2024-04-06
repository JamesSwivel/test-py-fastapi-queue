#!/usr/bin/env python3

import sys
import os
from typing import Union, Callable, TypeVar, List, TypedDict, Dict, Any, NamedTuple


########################################################
## Change to project root dir
########################################################
projRootDir = f"{os.path.dirname(__file__)}/.."
os.chdir(projRootDir)

########################################################
## Explicitly appends the search paths, where self-developed modules/packages are resided
## This helps consistent imports, without using relative paths.
########################################################
importDirs = ["./src/lib"]
sysDirsToAppend: List[str] = []
for importDir in importDirs:
    if os.path.exists(importDir) and os.path.isdir(importDir):
        sys.path.append(importDir)
        sysDirsToAppend.append(importDir)
if len(sysDirsToAppend) == 0:
    raise Exception(f"import dirs not found, targetPaths={importDirs}")

########################################################
## import self-developed modules/packages
########################################################
from app import App
import util as U


def main():
    App.main(__file__)


if __name__ == "__main__":
    main()
