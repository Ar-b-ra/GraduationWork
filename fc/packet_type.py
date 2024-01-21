from enum import Enum


class RequestTypes(str, Enum):
    SCOPE = "Scope"


class OscMethods(str, Enum):
    REQUEST = "request"
    DOWNLOAD = "download"
    SETUP = "setup"
    RESET = "reset"
