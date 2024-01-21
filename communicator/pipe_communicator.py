import os
import sys
from abc import abstractmethod
from pathlib import Path
from time import sleep
from typing import List, TextIO

from utility.logger import rootLogger

if sys.platform == "win32":
    import pywintypes
    import win32file


class Pipe:
    def __init__(self, name: [str, Path], is_input_pipe: bool):
        self.name = name
        self.is_input_pipe = is_input_pipe
        self.pipe: [TextIO, None] = None
        self.connect()

    @abstractmethod
    def connect(self):
        return

    def disconnect(self):
        self.pipe = None
        rootLogger.critical(f"Pipe {self.name} was disconnected")

    @abstractmethod
    def write_to_pipe(self, text) -> bool:
        return

    @abstractmethod
    def read_from_pipe(self) -> [str, None]:
        return


class PipeLinux(Pipe):
    def connect(self):
        if not Path(self.name).exists():
            rootLogger.warning(f"There is no {self.name} file! Creating new")
            try:
                os.mkfifo(self.name)
            except (
                FileExistsError
            ):  # может возникуть при одновременном создании пайпов имитатором или UMLConnector'ом
                pass
        if self.is_input_pipe:
            self.pipe = open(self.name, "r")
        else:
            self.pipe = open(self.name, "w")
        rootLogger.success(
            f"Pipe with name = {self.name} was opened, is_input = {self.is_input_pipe}"
        )

    def disconnect(self) -> None:
        try:
            os.remove(self.name)
        except FileNotFoundError:
            pass
        super().disconnect()

    def read_from_pipe(self) -> [List[str], None]:
        if not self.is_input_pipe or self.pipe is None:
            return None
        while (answer := self.pipe.readline()) is None:
            continue
        return list(filter(len, [answer]))

    def write_to_pipe(self, text):
        if self.is_input_pipe:
            return False
        else:
            self.pipe.writelines(text + "\n")
            self.pipe.flush()
            return True


class PipeWindows(Pipe):
    def connect(self):
        self.name = "\\\\.\\pipe\\" + self.name
        rootLogger.debug(f"Creating pipe {self.name}, {self.is_input_pipe=} ")

        access = (
            win32file.GENERIC_READ if self.is_input_pipe else win32file.GENERIC_WRITE
        )
        # TODO: выяснить, почему без задержки не работает (канал занят)
        sleep(1)
        self.pipe = win32file.CreateFile(
            self.name,
            access,
            0,  # win32file.FILE_SHARE_WRITE,  # no sharing
            None,  # default security attributes
            win32file.OPEN_EXISTING,
            0,  # default attributes
            None,
        )  # no template file
        rootLogger.debug(f"{self.pipe=}, {self.is_input_pipe=} ")
        rootLogger.success(
            f"Pipe with name = {self.name} was opened, is_input = {self.is_input_pipe}"
        )

    def read_from_pipe(self) -> [List[str], None]:
        if not self.is_input_pipe:
            return None
        try:
            _, answer = win32file.ReadFile(self.pipe, 64 * 1024)
        except pywintypes.error as exc:
            raise BrokenPipeError(exc)
        answer_list = answer.decode("UTF-8").split("\n")
        answer_list = list(filter(len, answer_list))  # фильтр пустых строк
        return answer_list

    def write_to_pipe(self, text) -> bool:
        if self.is_input_pipe:
            return False
        text = text + "\n"
        try:
            err, bytes_written = win32file.WriteFile(self.pipe, bytes(text, "UTF-8"))
            win32file.FlushFileBuffers(self.pipe)
        except pywintypes.error as exc:
            raise BrokenPipeError(exc)
        return True


class PipeCommunicator:
    def __init__(self, input_pipe: [str, Path], output_pipe: [str, Path]):
        self.input_pipe_name = input_pipe
        self.output_pipe_name = output_pipe
        self.input_pipe: Pipe = Pipe(input_pipe, is_input_pipe=True)
        self.output_pipe: Pipe = Pipe(output_pipe, is_input_pipe=False)
        self.is_connected = False

    def send(self, value):
        try:
            if self.is_connected:
                self.output_pipe.write_to_pipe(value)
        except BrokenPipeError as exc:
            rootLogger.critical(
                f"Pipe {self.output_pipe_name} was accidentally broken with error: {exc}"
            )
            self.close_connection()

    def receive(self) -> [List[str], None]:
        try:
            input_message = self.input_pipe.read_from_pipe()
            return input_message
        except BrokenPipeError as exc:
            rootLogger.critical(
                f"Pipe {self.input_pipe_name} was accidentally broken with error: {exc}"
            )
            self.close_connection()

    def open_connection(self):
        rootLogger.debug(sys.platform)
        if sys.platform == "win32":
            self.output_pipe = PipeWindows(self.output_pipe_name, is_input_pipe=False)
            self.input_pipe = PipeWindows(self.input_pipe_name, is_input_pipe=True)
        else:
            self.output_pipe = PipeLinux(self.output_pipe_name, is_input_pipe=False)
            self.input_pipe = PipeLinux(self.input_pipe_name, is_input_pipe=True)
        self.is_connected = True

    def close_connection(self):
        self.input_pipe.disconnect()
        self.output_pipe.disconnect()
        self.is_connected = False
