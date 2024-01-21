import json
import sys
import threading
from pathlib import Path
from queue import Queue
from subprocess import Popen
from typing import Optional, Union, Literal, Any, Tuple, Dict, List

from PyQt5.QtCore import QObject

from communicator.locked_queue import LockedPriorityQueue
from communicator.pipe_communicator import PipeCommunicator
from utility.logger import rootLogger

COMMUNICATOR_PATH = Path("bin", "JsonRpcPipesConnector")

if sys.platform == "win32":
    pipe_executable_path = Path(
        COMMUNICATOR_PATH, "JsonRpcPipesConnector.exe"
    ).absolute()
else:
    pipe_executable_path = Path(COMMUNICATOR_PATH, "JsonRpcPipesConnector").absolute()


class AsyncConnector(QObject):
    instance = None
    input_pipe_name = "asc_rx"
    output_pipe_name = "asc_tx"

    def __new__(
            cls,
            request_queue: Optional[LockedPriorityQueue],
            response_queue: Optional[Queue],
    ):
        if cls.instance is None:
            cls.instance = super(AsyncConnector, cls).__new__(
                cls, request_queue, response_queue
            )
        return cls.instance

    def __init__(
            self,
            request_queue: Optional[LockedPriorityQueue],
            response_queue: Optional[Queue],
    ):
        super(QObject, AsyncConnector).__init__(self)
        self._receive_thread = None
        self._send_thread = None
        self.answer_queue = response_queue
        self.request_queue = request_queue
        if not hasattr(self.instance, "is_connected"):
            self.pipe_communicator = PipeCommunicator(
                input_pipe=self.input_pipe_name, output_pipe=self.output_pipe_name
            )
            self.executable_args = [
                pipe_executable_path,
            ]
            self.is_connected = False

    def set_answer_queue(self, q):
        self.answer_queue = q

    def set_connection_params(
            self, connection_type: Literal["serial", "ethernet"], params: dict
    ) -> None:
        # to implement
        self.restart()

    def get_connection_params(self) -> Tuple[str, Dict[str, Any]]:
        connection_params = dict()
        connection_type = ""
        # to implement
        return connection_type, connection_params

    def create_connection(self):
        if self.is_connected:
            return
        if errors := self._validate_connection_params():
            rootLogger.warning("Incorrect connection params")
            for error in errors:
                rootLogger.error(error)
            return
        self._run_async_connector()
        self.pipe_communicator.input_pipe_name = self.input_pipe_name
        self.pipe_communicator.output_pipe_name = self.output_pipe_name
        self.pipe_communicator.open_connection()
        while not self.request_queue.empty():
            self.request_queue.get(block=True)
        self.is_connected = True
        self.request_queue.unlock()
        self._send_thread = threading.Thread(target=self._send, daemon=True)
        self._receive_thread = threading.Thread(target=self._receive, daemon=True)
        self._send_thread.start()
        self._receive_thread.start()
        rootLogger.success("Connection opened")

    def close_connection(self):
        if not self.is_connected:
            return
        self.is_connected = False
        self.request_queue.lock()
        self._stop_async_connector()
        self.pipe_communicator.close_connection()
        rootLogger.info("Connection closed")

    def _validate_connection_params(self) -> List[str]:
        errors = []
        # to implement
        return errors

    def _get_pipes_name(self) -> Tuple[str, str]:
        if sys.platform == "win32":
            rx_name = "\\\\.\\pipe\\" + self.output_pipe_name
            tx_name = "\\\\.\\pipe\\" + self.input_pipe_name
        else:
            rx_name = self.output_pipe_name
            tx_name = self.input_pipe_name
        return rx_name, tx_name

    def _run_async_connector(self):
        self.json_rpc = Popen(
            self.executable_args,
            stderr=open("stderr.txt", "w"),
            stdout=open("stdout.txt", "w"),
        )

    def _stop_async_connector(self):
        self.json_rpc.kill()

    def restart(self):
        if self.is_connected:
            self.close_connection()
            self.create_connection()

    def _send(self):
        while self.is_connected and self.pipe_communicator.is_connected:
            if prepared_request := self.request_queue.get():
                rootLogger.debug(f"{prepared_request = }")
                self.pipe_communicator.send(prepared_request)
                self.request_queue.task_done()
        self.close_connection()

    def _receive(self):
        while self.is_connected and self.pipe_communicator.is_connected:
            answer_list = self.pipe_communicator.receive()
            if not answer_list:
                continue
            rootLogger.debug(f"{answer_list = }")
            for answer in answer_list:
                prepared_answer = json.loads(answer)
                rootLogger.debug(f"{prepared_answer = }")
                request_to_manage, answer_value = prepared_answer.popitem()
                request_to_manage = json.loads(request_to_manage)
                if self.answer_queue is not None:
                    self.answer_queue.put((request_to_manage, answer_value))
        self.close_connection()
