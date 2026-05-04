# -*- coding: utf-8 -*-
"""
Task Manager for Sudan Data Loader.

Provides async operations using QgsTask for non-blocking operations.
"""

from qgis.core import (
    QgsTask, QgsApplication, QgsMessageLog, Qgis
)
from qgis.PyQt.QtCore import QObject, pyqtSignal


class SudanDataTask(QgsTask):
    """Base task class for Sudan Data Loader async operations."""

    # Signals for task completion
    task_completed = pyqtSignal(object)  # result data
    task_failed = pyqtSignal(str)  # error message
    task_progress = pyqtSignal(int, str)  # progress percent, message

    def __init__(self, description, task_func, *args, **kwargs):
        """
        Initialize the task.

        :param description: Task description for display
        :param task_func: Function to execute (receives self as first arg for progress updates)
        :param args: Arguments to pass to task_func
        :param kwargs: Keyword arguments to pass to task_func
        """
        super().__init__(description, QgsTask.CanCancel)
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs
        self.result_data = None
        self.error_message = None

    def run(self):
        """Execute the task."""
        try:
            # Call the task function with self for progress updates
            self.result_data = self.task_func(self, *self.args, **self.kwargs)
            return True
        except Exception as e:
            self.error_message = str(e)
            QgsMessageLog.logMessage(
                f"Task failed: {self.error_message}",
                "Sudan Data Loader",
                Qgis.Critical
            )
            return False

    def finished(self, result):
        """Handle task completion."""
        if result:
            self.task_completed.emit(self.result_data)
        else:
            self.task_failed.emit(self.error_message or "Unknown error")

    def cancel(self):
        """Cancel the task."""
        QgsMessageLog.logMessage(
            f"Task cancelled: {self.description()}",
            "Sudan Data Loader",
            Qgis.Info
        )
        super().cancel()

    def update_progress(self, percent, message=''):
        """
        Update task progress.

        :param percent: Progress percentage (0-100)
        :param message: Optional progress message
        """
        self.setProgress(percent)
        if message:
            self.task_progress.emit(percent, message)


class TaskManager(QObject):
    """Manager for Sudan Data Loader async tasks."""

    # Signals
    all_tasks_complete = pyqtSignal()
    task_started = pyqtSignal(str)  # task description
    task_finished = pyqtSignal(str, bool)  # task description, success

    def __init__(self):
        """Initialize the task manager."""
        super().__init__()
        self.active_tasks = {}
        self.task_counter = 0

    def run_task(self, description, task_func, *args, callback=None, error_callback=None, **kwargs):
        """
        Run a function as an async task.

        :param description: Task description
        :param task_func: Function to execute
        :param args: Function arguments
        :param callback: Success callback (receives result)
        :param error_callback: Error callback (receives error message)
        :param kwargs: Function keyword arguments
        :returns: Task ID
        """
        task = SudanDataTask(description, task_func, *args, **kwargs)

        # Connect signals
        if callback:
            task.task_completed.connect(callback)
        if error_callback:
            task.task_failed.connect(error_callback)

        # Track task
        self.task_counter += 1
        task_id = f"task_{self.task_counter}"
        self.active_tasks[task_id] = task

        task.taskCompleted.connect(lambda: self._on_task_complete(task_id))
        task.taskTerminated.connect(lambda: self._on_task_complete(task_id))

        # Add to QGIS task manager
        QgsApplication.taskManager().addTask(task)

        self.task_started.emit(description)
        QgsMessageLog.logMessage(
            f"Task started: {description}",
            "Sudan Data Loader",
            Qgis.Info
        )

        return task_id

    def _on_task_complete(self, task_id):
        """Handle task completion."""
        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            success = task.result_data is not None
            self.task_finished.emit(task.description(), success)

            if not self.active_tasks:
                self.all_tasks_complete.emit()

    def cancel_task(self, task_id):
        """
        Cancel a running task.

        :param task_id: Task ID to cancel
        """
        if task_id in self.active_tasks:
            self.active_tasks[task_id].cancel()

    def cancel_all_tasks(self):
        """Cancel all running tasks."""
        for task in self.active_tasks.values():
            task.cancel()

    def get_active_task_count(self):
        """Get number of active tasks."""
        return len(self.active_tasks)

    def is_busy(self):
        """Check if any tasks are running."""
        return len(self.active_tasks) > 0


# Convenience functions for common async operations

def download_async(url, callback, error_callback=None, description="Downloading..."):
    """
    Download a file asynchronously.

    :param url: URL to download
    :param callback: Success callback (receives file path)
    :param error_callback: Error callback
    :param description: Task description
    """
    def download_task(task, url):
        import tempfile
        import os
        from qgis.core import QgsBlockingNetworkRequest
        from qgis.PyQt.QtCore import QUrl
        from qgis.PyQt.QtNetwork import QNetworkRequest

        task.update_progress(0, "Starting download...")

        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.RedirectPolicyAttribute,
            QNetworkRequest.NoLessSafeRedirectPolicy
        )

        blocking = QgsBlockingNetworkRequest()
        error = blocking.get(request, forceRefresh=True)

        if task.isCanceled():
            return None

        task.update_progress(50, "Processing response...")

        if error != QgsBlockingNetworkRequest.NoError:
            raise Exception(f"Download failed: {blocking.errorMessage()}")

        data = bytes(blocking.reply().content())
        if not data:
            raise Exception("Downloaded file is empty")

        # Save to temp file
        filename = url.split('/')[-1].split('?')[0] or 'download'
        filepath = os.path.join(tempfile.gettempdir(), f"sudan_dl_{filename}")

        with open(filepath, 'wb') as f:
            f.write(data)

        task.update_progress(100, "Download complete")
        return filepath

    manager = get_task_manager()
    return manager.run_task(
        description,
        download_task,
        url,
        callback=callback,
        error_callback=error_callback
    )


def process_async(process_func, args, callback, error_callback=None, description="Processing..."):
    """
    Run a processing function asynchronously.

    :param process_func: Function to run (should accept task as first arg)
    :param args: Arguments for the function
    :param callback: Success callback
    :param error_callback: Error callback
    :param description: Task description
    """
    manager = get_task_manager()
    return manager.run_task(
        description,
        process_func,
        *args,
        callback=callback,
        error_callback=error_callback
    )


# Global task manager instance
_task_manager = None


def get_task_manager():
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager
