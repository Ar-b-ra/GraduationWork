import json
from typing import Dict, Optional

from fc.packet_type import *
from communicator.locked_queue import LockedPriorityQueue
from utility.logger import rootLogger


def decorate_arguments(arguments_dict: dict) -> dict:
    decorated_dict = dict()
    for key, val in arguments_dict.items():
        if val in (float("inf"), float("-inf")):
            decorated_dict[key] = str(val)
        elif isinstance(val, dict):
            decorated_dict[key] = decorate_arguments(val)
        else:
            decorated_dict[key] = val
    return decorated_dict


class FC_Controls:
    def __init__(self):
        self.request_queue: Optional[LockedPriorityQueue] = None

    def set_request_queue(self, request_queue: LockedPriorityQueue) -> None:
        self.request_queue = request_queue

    @staticmethod
    def make_command(command_type: RequestTypes, name, method, arguments=None):
        final_request = {"Type": command_type, "Name": name, "Method": method}
        if arguments is not None:
            final_request["Arguments"] = arguments
        return final_request

    def make_request(self, async_request: Dict):
        if not self.request_queue.locked:
            prepared_request = json.dumps(decorate_arguments(async_request))
            rootLogger.debug(f"{prepared_request = }")
            self.request_queue.put(prepared_request)

    def make_request_without_decorate(self, async_request: Dict):
        if not self.request_queue.locked:
            prepared_request = json.dumps(async_request)
            rootLogger.debug(f"{prepared_request = }")
            self.make_request(async_request)