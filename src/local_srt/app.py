from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import SUPPORTED_INPUT_EXTENSIONS, bundled_base_dir


def _import_qt():
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except Exception as exc:
        raise RuntimeError("PySide6 is required for the desktop app. Install with pip install -e .") from exc
    return QtCore, QtGui, QtWidgets


@dataclass
class Job:
    input_path: Path
    output_path: Path
    status: str = "Queued"
    percent: int = 0


def worker_command() -> list[str]:
    base = bundled_base_dir()
    exe = base / "subtitle-worker.exe"
    if exe.exists():
        return [str(exe)]
    if sys.platform == "win32":
        python_exe = Path(sys.executable)
        if python_exe.name.lower() == "pythonw.exe":
            console_python = python_exe.with_name("python.exe")
            if console_python.exists():
                return [str(console_python), "-m", "local_srt.worker"]
    return [sys.executable, "-m", "local_srt.worker"]


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS


def main() -> int:
    QtCore, QtGui, QtWidgets = _import_qt()

    class DropList(QtWidgets.QListWidget):
        files_dropped = QtCore.Signal(list)

        def __init__(self) -> None:
            super().__init__()
            self.setAcceptDrops(True)
            self.setAlternatingRowColors(True)

        def dragEnterEvent(self, event):
            if event.mimeData().hasUrls():
                event.acceptProposedAction()

        def dragMoveEvent(self, event):
            event.acceptProposedAction()

        def dropEvent(self, event):
            paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("Local SRT")
            self.resize(860, 560)
            self.jobs: list[Job] = []
            self.current_index = -1
            self.process: QtCore.QProcess | None = None
            self.stdout_buffer = ""

            central = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(central)

            header = QtWidgets.QLabel("Drop audio or video files to create SRT subtitles")
            header.setStyleSheet("font-size: 20px; font-weight: 600;")
            layout.addWidget(header)

            self.list_widget = DropList()
            self.list_widget.files_dropped.connect(self.add_files)
            layout.addWidget(self.list_widget, 1)

            settings = QtWidgets.QHBoxLayout()
            settings.addWidget(QtWidgets.QLabel("Device"))
            self.device_combo = QtWidgets.QComboBox()
            self.device_combo.addItem("GPU (NVIDIA CUDA)", "cuda")
            self.device_combo.addItem("CPU (slow)", "cpu")
            default_device = os.environ.get("LOCAL_SRT_DEFAULT_DEVICE", "cuda")
            default_device_index = self.device_combo.findData(default_device)
            if default_device_index >= 0:
                self.device_combo.setCurrentIndex(default_device_index)
            settings.addWidget(self.device_combo)
            settings.addStretch(1)
            layout.addLayout(settings)

            controls = QtWidgets.QHBoxLayout()
            self.add_button = QtWidgets.QPushButton("Add Files")
            self.add_button.clicked.connect(self.choose_files)
            controls.addWidget(self.add_button)

            self.start_button = QtWidgets.QPushButton("Start")
            self.start_button.clicked.connect(self.start_jobs)
            controls.addWidget(self.start_button)

            self.clear_button = QtWidgets.QPushButton("Clear")
            self.clear_button.clicked.connect(self.clear_jobs)
            controls.addWidget(self.clear_button)

            controls.addStretch(1)
            self.progress = QtWidgets.QProgressBar()
            self.progress.setRange(0, 100)
            self.progress.setFixedWidth(220)
            controls.addWidget(self.progress)
            layout.addLayout(controls)

            self.log = QtWidgets.QPlainTextEdit()
            self.log.setReadOnly(True)
            self.log.setMaximumBlockCount(500)
            layout.addWidget(self.log)

            self.setCentralWidget(central)

        def choose_files(self) -> None:
            patterns = "Media files (*.mp3 *.wav *.m4a *.mp4 *.mkv *.mov *.flac *.aac *.webm);;All files (*.*)"
            files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Choose media files", "", patterns)
            self.add_files([Path(f) for f in files])

        def add_files(self, paths: list[Path]) -> None:
            for path in paths:
                if path.is_file() and is_supported_file(path):
                    job = Job(input_path=path, output_path=path.with_suffix(".srt"))
                    self.jobs.append(job)
                    self.list_widget.addItem(f"{path.name} -> {job.output_path.name}    [{job.status}]")
                elif path.is_file():
                    self.log.appendPlainText(f"Skipped unsupported file: {path}")

        def clear_jobs(self) -> None:
            if self.process and self.process.state() != QtCore.QProcess.NotRunning:
                self.log.appendPlainText("A job is running; wait for it to finish before clearing.")
                return
            self.jobs.clear()
            self.current_index = -1
            self.list_widget.clear()
            self.progress.setValue(0)
            self.log.clear()

        def start_jobs(self) -> None:
            if not self.jobs:
                self.log.appendPlainText("Add at least one media file first.")
                return
            self.start_button.setEnabled(False)
            self.add_button.setEnabled(False)
            self.device_combo.setEnabled(False)
            self.current_index = -1
            self.start_next_job()

        def start_next_job(self) -> None:
            self.current_index += 1
            if self.current_index >= len(self.jobs):
                self.log.appendPlainText("All jobs finished.")
                self.start_button.setEnabled(True)
                self.add_button.setEnabled(True)
                self.device_combo.setEnabled(True)
                self.progress.setValue(100)
                return
            job = self.jobs[self.current_index]
            job.status = "Starting"
            job.percent = 0
            self.refresh_job_row(self.current_index)
            self.progress.setValue(0)

            args = worker_command() + [
                "transcribe",
                "--input",
                str(job.input_path),
                "--output",
                str(job.output_path),
                "--language",
                "auto",
                "--model",
                "1.7b",
                "--device",
                str(self.device_combo.currentData()),
                "--script",
                "traditional",
                "--caption-style",
                "natural",
            ]
            self.log.appendPlainText(f"Starting: {job.input_path}")
            self.stdout_buffer = ""
            self.process = QtCore.QProcess(self)
            self.process.setProgram(args[0])
            self.process.setArguments(args[1:])
            self.process.readyReadStandardOutput.connect(self.on_stdout)
            self.process.readyReadStandardError.connect(self.on_stderr)
            self.process.finished.connect(self.on_finished)
            self.process.start()

        def on_stdout(self) -> None:
            assert self.process is not None
            data = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.stdout_buffer += data
            lines = self.stdout_buffer.splitlines(keepends=True)
            self.stdout_buffer = ""
            if lines and not lines[-1].endswith(("\n", "\r")):
                self.stdout_buffer = lines.pop()
            for line in lines:
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    self.log.appendPlainText(line)
                    continue
                self.handle_event(event)

        def on_stderr(self) -> None:
            assert self.process is not None
            data = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
            if data.strip():
                self.log.appendPlainText(data.strip())

        def handle_event(self, event: dict) -> None:
            if self.current_index < 0 or self.current_index >= len(self.jobs):
                return
            job = self.jobs[self.current_index]
            event_type = event.get("type")
            if event_type == "status":
                job.status = str(event.get("message", "Working"))
                self.log.appendPlainText(job.status)
            elif event_type == "progress":
                job.status = str(event.get("stage", "Working"))
                job.percent = int(event.get("percent", 0))
                self.progress.setValue(job.percent)
            elif event_type == "result":
                job.status = f"Done: {event.get('srt_path')}"
                job.percent = 100
                self.progress.setValue(100)
                self.log.appendPlainText(job.status)
            elif event_type == "error":
                job.status = "Failed"
                self.log.appendPlainText(f"Error: {event.get('message')}")
            self.refresh_job_row(self.current_index)

        def on_finished(self, exit_code: int, _status) -> None:
            if self.stdout_buffer.strip():
                try:
                    self.handle_event(json.loads(self.stdout_buffer))
                except json.JSONDecodeError:
                    self.log.appendPlainText(self.stdout_buffer.strip())
            self.stdout_buffer = ""
            if self.current_index >= 0 and self.current_index < len(self.jobs):
                job = self.jobs[self.current_index]
                if exit_code != 0 and job.status != "Failed":
                    job.status = f"Failed with exit code {exit_code}"
                self.refresh_job_row(self.current_index)
            self.start_next_job()

        def refresh_job_row(self, index: int) -> None:
            job = self.jobs[index]
            item = self.list_widget.item(index)
            if item:
                item.setText(f"{job.input_path.name} -> {job.output_path.name}    [{job.percent}% {job.status}]")

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Local SRT")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
