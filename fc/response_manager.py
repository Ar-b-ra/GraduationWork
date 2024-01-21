import threading
from queue import Queue

from PyQt5.QtCore import QObject, pyqtSignal

from fc.packet_type import (
    OscMethods,
    RequestTypes,
)
from utility.logger import rootLogger


class ResponseManager(QObject):
    oscill_set_trigger_signal = pyqtSignal(bool)
    oscill_reset_trigger_signal = pyqtSignal(bool)
    oscill_set_trigger_get_data_signal = pyqtSignal(dict, dict, float)
    oscill_get_data_signal = pyqtSignal(dict, dict, float)

    def __init__(self, response_queue: Queue):
        super(QObject, ResponseManager).__init__(self)
        self.manage_answer_thread = threading.Thread(
            target=self.manage_answers, daemon=True
        )
        self.response_queue = response_queue
        self.manage_answer_thread.start()

        self.request_type_dict = {
            RequestTypes.SCOPE: self._resolve_scope_request,
        }

    def manage_answers(self):
        while True:
            if prepared_request := self.response_queue.get():
                rootLogger.trace(f"{prepared_request = }")
                _request, _value = prepared_request
                self._manage_answers(_request, _value)
                self.response_queue.task_done()

    def _manage_answers(self, request: dict, answer_value: dict):
        request_type, request_method = request["Type"], request["Method"]
        request_name = request["Name"]
        rootLogger.info(f"Got answer for {request = } with {answer_value = }")

        if resolving_command := self.request_type_dict.get(request_type):
            resolving_command(
                request_method=request_method,
                request_name=request_name,
                answer_value=answer_value,
            )
        else:
            rootLogger.critical(
                f"Incorrect answer type for {request = } with {answer_value = }"
            )

    def _resolve_scope_request(
        self, request_method, request_name: str, answer_value: dict
    ):
        if request_method == OscMethods.SETUP:
            value = answer_value.get("value")
            if value is not None:
                self.oscill_set_trigger_signal.emit(value)
        elif request_method in (OscMethods.DOWNLOAD, OscMethods.REQUEST):
            answer_value_data = answer_value.get("data")
            answer_start = answer_value.get("start")
            answer_time = answer_value.get("time")
            if all(
                [
                    answer_value_data is not None,
                    answer_start is not None,
                    answer_time is not None,
                ]
            ):
                self.oscill_get_data_signal.emit(
                    answer_value_data, {"time": answer_time}, answer_start
                )
        elif request_method == OscMethods.RESET:
            self.oscill_reset_trigger_signal.emit(True)
