import sys
import os
import json
import argparse
from typing import Union, Callable, TypeVar, List, TypedDict, Dict, Any, NamedTuple, Literal

import util as U
from .appConfig import AppConfig
import appTest

U.isDirExist("./")

# U.logD(f"Loading name={__name__}, file={__file__}")

## min python requirement 3.8.1
assert sys.version_info >= (3, 8, 1)


class TGv_script(TypedDict):
    filePath: str
    args: Any


class TGv_server(TypedDict):
    id: str
    port: int


class TGv(TypedDict):
    script: TGv_script
    server: TGv_server
    testCase: str


class App:
    ## App global variable
    Gv: TGv = {"script": {"filePath": "", "args": None}, "server": {"id": "", "port": 5000}, "testCase": ""}

    @classmethod
    def main(cls, scriptFilePath: str):
        funcName = cls.main.__name__
        prefix = funcName
        try:
            U.logI(f"python ver={U.pythonVer()['verStr']}")

            U.logI(f"pid={os.getpid()}")

            ## change CWD from main script filePath
            cls.Gv["script"]["filePath"] = scriptFilePath
            U.logI(f"cwd={os.getcwd()}")

            ## parse cmd args and validate with cfg
            cls.parseArgs()

            ## test case
            testCase = cls.Gv["testCase"]
            if testCase == "log":
                appTest.testPrintLog()
            elif testCase == "ex1":
                appTest.testExceptionCases(1)
            elif testCase == "ex2":
                appTest.testExceptionCases(2)
            elif testCase == "ex3":
                appTest.testExceptionCases(3)

        except Exception as e:
            U.logPrefixE(prefix, f"Failed to start the serverApp[{AppConfig.APP_NAME}], err={e}")

    @classmethod
    def parseArgs(cls):
        funcName = cls.parseArgs.__name__
        prefix = funcName
        try:
            parser = argparse.ArgumentParser(description="App server")
            parser.formatter_class = argparse.RawDescriptionHelpFormatter

            subparsers = parser.add_subparsers(title="test cases", dest="test")
            subparsers.add_parser("log", help="print test logs")
            subparsers.add_parser("ex1", help="print exception error log (1 level)")
            subparsers.add_parser("ex2", help="print exception error log (2 level)")
            subparsers.add_parser("ex3", help="print exception error log (3 level)")
            subparsers.add_parser("all", help="print all cases")
            parser.add_argument(
                "--test",
                required=True,
                help="perform test case",
            )

            parser.add_argument(
                "--id",
                required=False,
                help="app server id",
            )
            parser.add_argument(
                "--port",
                required=False,
                help="app server port",
            )
            parser.add_argument(
                "--autoStart",
                required=False,
                help="auto start app server (default is False)",
            )
            parser.add_argument(
                "--cfg",
                required=False,
                help="specify cfg jsonc",
            )
            args = parser.parse_args()

            #################################
            ## check args
            #################################
            if args.test:
                cls.Gv["testCase"] = args.test

            if args.port:
                # if not U.isIntStr(args.port, {"min": 1}):
                #     raise Exception(f"invalid port={args.port}")
                port = int(args.port)
                cls.Gv["server"]["port"] = port

            cls.Gv["script"]["args"] = args

        except Exception as e:
            U.throwPrefix(prefix, e)
