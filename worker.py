import threading
from pathlib import Path
from typing import List, Callable, Dict, Any, Optional
from cleaner import clean_folders


class CleanerWorker:
    """
    Background worker that runs the folder cleaning process in a dedicated
    thread while providing thread-safe callbacks to the UI.
    """

    def __init__(
        self,
        folders: List[Path],
        on_progress: Callable[[str, int, int], None],
        on_prompt_skip: Callable[[Path, bool, str], Any],
        on_complete: Callable[[Dict[str, Any]], None],
        on_error: Callable[[Exception], None],
        post_to_ui: Callable[[Callable[[], None]], None],
    ):
        self.folders = folders
        self.on_progress = on_progress
        self.on_prompt_skip = on_prompt_skip
        self.on_complete = on_complete
        self.on_error = on_error
        self.post_to_ui = post_to_ui

        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._batch_action: Optional[str] = None

    def start(self) -> None:
        """Starts the worker thread."""
        self._cancel_event.clear()
        self._batch_action = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Requests graceful cancellation of the cleaning process."""
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        """Checks if cancellation has been requested."""
        return self._cancel_event.is_set()

    def _safe_progress(self, current_path: str, cleaned_count: int, total_items: int) -> None:
        """Dispatches progress updates to the UI thread."""
        self.post_to_ui(lambda: self.on_progress(current_path, cleaned_count, total_items))

    def _safe_prompt_skip(self, item_path: Path, is_dir: bool, error_msg: str) -> str:
        """
        Synchronously requests user input on the UI thread for locked/in-use files.
        If the user previously checked 'Do this for all current items', reuses that action.
        Blocks the worker thread until the user makes a decision.
        """
        if self._batch_action is not None:
            return self._batch_action

        response_event = threading.Event()
        decision_holder = {"action": "skip", "apply_to_all": False}

        def ask_in_ui() -> None:
            try:
                res = self.on_prompt_skip(item_path, is_dir, error_msg)
                if isinstance(res, tuple):
                    action, apply_to_all = res
                elif isinstance(res, bool):
                    action, apply_to_all = ("skip" if res else "abort"), False
                else:
                    action, apply_to_all = str(res), False
                decision_holder["action"] = action
                decision_holder["apply_to_all"] = apply_to_all
            finally:
                response_event.set()

        self.post_to_ui(ask_in_ui)
        response_event.wait()

        if decision_holder["apply_to_all"]:
            self._batch_action = decision_holder["action"]

        return decision_holder["action"]

    def _run(self) -> None:
        """Worker thread entry point."""
        try:
            summary = clean_folders(
                folders=self.folders,
                progress_fn=self._safe_progress,
                prompt_skip_fn=self._safe_prompt_skip,
                is_cancelled_fn=self.is_cancelled,
            )
            self.post_to_ui(lambda: self.on_complete(summary))
        except Exception as exc:
            self.post_to_ui(lambda: self.on_error(exc))
