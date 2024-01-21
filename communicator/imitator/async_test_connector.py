import threading
from pathlib import Path
from queue import PriorityQueue, Queue
from time import sleep
from typing import Optional, Union

from communicator.async_communicator import AsyncConnector
from communicator.imitator.pipe_read_write import Imitator


class AsyncConnectorTest(AsyncConnector):
    def __init__(
        self,
        request_queue: Optional[PriorityQueue] = None,
        response_queue: Optional[Queue] = None,
    ):
        super().__init__(request_queue, response_queue)
        if not hasattr(self.instance, "_imitator"):
            self.thread1: Optional[threading.Thread] = None
            self._imitator = Imitator()

    def __new__(
        cls,
        request_queue: Optional[PriorityQueue] = None,
        response_queue: Optional[Queue] = None,
    ):
        if cls.instance is None:
            cls.instance = super(AsyncConnectorTest, cls).__new__(
                cls, request_queue, response_queue
            )
            AsyncConnector.instance = cls.instance
        return cls.instance

    def _validate_connection_params(self):
        return []

    def get_data_from_ini(self, ini_file_path: Union[Path, str]):
        self._imitator.prepare_data_from_json(ini_file_path)

    def get_connection_params(self):
        return "test", dict()

    def _run_async_connector(self):
        self.thread1 = threading.Thread(target=self._imitator.start)
        self.thread1.start()
        sleep(1)

    def _stop_async_connector(self):
        # self.thread1.join()
        self._imitator.stop()
        self.thread1 = None
