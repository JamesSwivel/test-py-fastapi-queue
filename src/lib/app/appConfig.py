import sys
import os
from typing import Final, Union, Callable, TypeVar, List, TypedDict, Dict, Any

import util as U

# U.logD(f"Loading name={__name__}, file={__file__}")


class AppConfig:
    APP_NAME: Final[str] = "swivel"
