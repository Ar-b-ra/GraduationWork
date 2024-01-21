import json
import os
import random
import sys
from pathlib import Path
from threading import Thread
from typing import Union

from fc.packet_type import (
    RequestTypes,
    OscMethods,
    ProcedureMethods,
    SignalMethods,
    SettingMethods,
    MovementsMethods,
    StatusMethods,
    MovementStates,
)


if sys.platform == "win32":
    import pywintypes
    import win32file
    import win32pipe

bufSize = 8192


def create_win_pipes():
    request_pipe_name = r"\\.\pipe\asc_tx"
    response_pipe_name = r"\\.\pipe\asc_rx"
    request_pipe = win32pipe.CreateNamedPipe(
        request_pipe_name,
        win32pipe.PIPE_ACCESS_INBOUND,
        win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
        4,  # number of instances
        bufSize,  # output buffer size
        bufSize,  # input buffer size
        0,  # default time-out
        None,  # security attributes
    )
    response_pipe = win32pipe.CreateNamedPipe(
        response_pipe_name,
        win32pipe.PIPE_ACCESS_OUTBOUND,
        win32pipe.PIPE_TYPE_BYTE | win32pipe.PIPE_READMODE_BYTE | win32pipe.PIPE_WAIT,
        4,  # number of instances
        bufSize,  # output buffer size
        bufSize,  # input buffer size
        0,  # default time-out
        None,  # security attributes
    )

    def wait_connection():
        win32pipe.ConnectNamedPipe(request_pipe, None)
        win32pipe.ConnectNamedPipe(response_pipe, None)
        print("CONNECTED")

    thread1 = Thread(target=wait_connection)
    thread1.start()
    return request_pipe, response_pipe


def connect_linux():
    if not Path("asc_tx").exists():
        try:
            os.mkfifo("asc_tx")
        except FileExistsError:
            pass
    request_pipe = open("asc_tx", "r")
    if not Path("asc_rx").exists():
        try:
            os.mkfifo("asc_rx")
        except FileExistsError:
            pass
    response_pipe = open("asc_rx", "w")
    return request_pipe, response_pipe


def read_from_pipe_windows(pipe) -> str:
    try:
        err, answer = win32file.ReadFile(pipe, bufSize)
        return answer.decode("UTF-8")
    except pywintypes.error:
        raise BrokenPipeError


def read_from_pipe_linux(pipe) -> str:
    return pipe.readline()


def write_to_pipe_windows(pipe, text: str):
    try:
        win32file.WriteFile(pipe, bytes(text + "\n", "UTF-8"))
        win32file.FlushFileBuffers(pipe)
    except pywintypes.error as exc:
        raise BrokenPipeError(exc)


def write_to_pipe_linux(pipe, text: str):
    pipe.writelines(text + "\n")
    pipe.flush()


def load_settings(data):
    nodes = data.get("nodes", [])
    for node in nodes:
        if node.get("setting_name") and node.get("enable"):
            yield node["title"], node["outputs"][0]["link_id"], node[
                "setting_name"
            ], node["params"], node.get("group"), node.get("level", 3)


def load_named_signals(data):
    nodes = data.get("nodes", [])
    for node in nodes:
        if node["title"] in ["Signal", "Status"]:
            socket = node["inputs"][0]
            yield (
                socket["link_id"],
                node["object_name"],
                socket.get("description", ""),
                node["title"],
                node["group"],
                node.get("alias", ""),
            )


def load_procedures(data):
    nodes = data.get("nodes", [])
    for node in nodes:
        if node.get("title") == "Procedure" and node.get("enable"):
            yield node["object_name"], node["params"].get("output", {}).keys()


def load_diagrams(data):
    nodes = data.get("nodes", [])
    for node in nodes:
        if node.get("title") == "Diagram" and node.get("enable"):
            yield node["object_name"]


class Imitator:
    def __init__(self):
        self.is_running = False
        self.handlers = {
            (RequestTypes.SCOPE, OscMethods.DOWNLOAD): self.handle_scope_download,
            (RequestTypes.SCOPE, OscMethods.REQUEST): self.handle_scope_request,
            (RequestTypes.SCOPE, OscMethods.SETUP): self.handle_scope_setup,
            (RequestTypes.SCOPE, OscMethods.RESET): self.handle_scope_reset,
        }

    @staticmethod
    def prepare_data(json_data: dict):
        settings, signals, statuses, procedures, diagrams = [], [], [], [], []
        # to implement
        return settings, signals, statuses, procedures, diagrams

    def start(self):
        self.is_running = True
        self._run()

    def stop(self):
        self.is_running = False
        print("Closing Imitator")

    def prepare_data_from_json(self, configuration_path: Union[str, Path]):
        # to implement
        pass

    def prepare_oscill_answer(self):
        pass
        # to implement

    def _run(self):
        if sys.platform == "win32":
            self.request_pipe, self.response_pipe = create_win_pipes()
            self.read_from_pipe = read_from_pipe_windows
            self.write_to_pipe = write_to_pipe_windows
        else:
            self.request_pipe, self.response_pipe = connect_linux()
            self.read_from_pipe = read_from_pipe_linux
            self.write_to_pipe = write_to_pipe_linux

        print(f"Execution path = {Path().absolute()}")

        while self.is_running:
            try:
                request = self.read_from_pipe(self.request_pipe)

                if not request:
                    print(f"Empty {request = }")
                    continue
                else:
                    print(f"Not empty {request = }")
                    request = json.loads(request)

                answer = self.handle_request(request)
                if answer:
                    self.write_to_pipe(self.response_pipe, json.dumps(answer))
                print(f"{answer = }")
            except BrokenPipeError as exc:
                print(f"[{type(exc)}]: {exc}")

    def handle_request(self, request):
        request_type = request.get("Type")
        request_method = request.get("Method")
        handler = self.handlers.get((request_type, request_method))
        if handler:
            return handler(request)
        else:
            print("Incorrect request")



    def handle_scope_download(self, request):
        if self.current_signals_to_oscill:
            prepared_answer = self.prepare_oscill_answer()
            return {json.dumps(request): prepared_answer}
        return None

    def handle_scope_request(self, request):
        if self.current_signals_to_oscill:
            prepared_answer = self.prepare_oscill_answer()
            return {json.dumps(request): prepared_answer}
        return None

    def handle_scope_setup(self, request):
        self.current_signals_to_oscill = request["Arguments"].get("Values")
        self.pre_trigger_time = request["Arguments"].get("PreTrigger")
        self.post_trigger_time = request["Arguments"].get("PostTrigger")
        if self.current_signals_to_oscill:
            prepared_answer = self.prepare_oscill_answer()
            return {json.dumps(request): prepared_answer}
        return None

    def handle_scope_reset(self, request):
        self.current_signals_to_oscill.clear()
        self.pre_trigger_time = None
        self.post_trigger_time = None
        return {json.dumps(request): None}
