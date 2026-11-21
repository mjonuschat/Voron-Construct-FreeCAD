"""Run work on Qt's thread pool and deliver its callbacks on the GUI thread."""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore


class _Dispatcher(QtCore.QObject):
    """Lives in the GUI thread; signals emitted from workers are queued to it."""

    deliver = QtCore.Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self.deliver.connect(self._call, QtCore.Qt.QueuedConnection)

    @QtCore.Slot(object, object)
    def _call(self, callback, value) -> None:
        callback(value)


class _Task(QtCore.QRunnable):
    def __init__(self, work, on_done, on_error, dispatcher: _Dispatcher) -> None:
        super().__init__()
        self._work = work
        self._on_done = on_done
        self._on_error = on_error
        self._dispatcher = dispatcher

    def run(self) -> None:
        try:
            result = self._work()
        except Exception as exc:  # deliver any worker error to the GUI thread
            self._dispatcher.deliver.emit(self._on_error, exc)
        else:
            self._dispatcher.deliver.emit(self._on_done, result)


_dispatcher: _Dispatcher | None = None


def run_async(
    work: Callable[[], object],
    on_done: Callable[[object], None],
    on_error: Callable[[Exception], None],
) -> None:
    """Run `work` off the GUI thread and report back on the GUI thread.

    Calls on_done(result) or on_error(exc).

    Must be called from the GUI thread, which owns the dispatcher.
    """
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = _Dispatcher()
    QtCore.QThreadPool.globalInstance().start(
        _Task(work, on_done, on_error, _dispatcher)
    )
