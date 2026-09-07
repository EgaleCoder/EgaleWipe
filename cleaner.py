import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Dict, Any, Tuple


def scan_folder_items(folder_path: Path) -> int:
    """Recursively counts all files and directories inside a folder."""
    if not folder_path.exists() or not folder_path.is_dir():
        return 0

    count = 0
    try:
        for root, dirs, files in os.walk(folder_path):
            count += len(files) + len(dirs)
    except Exception:
        pass
    return count


def scan_all_folders(folders: List[Path]) -> int:
    """Calculates the total number of items across all provided folders."""
    return sum(scan_folder_items(f) for f in folders)


def delete_single_file(
    file_path: Path,
    prompt_skip_fn: Optional[Callable[[Path, bool, str], str]] = None,
) -> Tuple[str, int]:
    """
    Attempts to delete a single file.
    If deletion fails, calls prompt_skip_fn(file_path, is_dir=False, error_message).
    Returns a tuple of (status, bytes_freed): ('deleted'|'skipped'|'abort', int).
    """
    file_size = 0
    try:
        file_size = file_path.stat().st_size
    except Exception:
        file_size = 0

    while True:
        try:
            # If file is read-only on Windows, remove read-only attribute
            if not os.access(file_path, os.W_OK):
                os.chmod(file_path, 0o777)
            file_path.unlink()
            return "deleted", file_size
        except Exception as exc:
            if prompt_skip_fn:
                action = prompt_skip_fn(file_path, False, str(exc))
                if isinstance(action, bool):
                    action = "skip" if action else "abort"
                if action == "retry":
                    continue
                elif action == "skip":
                    return "skipped", 0
                else:
                    return "abort", 0
            return "abort", 0


def delete_single_dir(
    dir_path: Path,
    prompt_skip_fn: Optional[Callable[[Path, bool, str], str]] = None,
) -> str:
    """
    Attempts to remove an empty directory.
    Returns 'deleted', 'skipped', or 'abort'.
    """
    while True:
        try:
            dir_path.rmdir()
            return "deleted"
        except Exception as exc:
            if prompt_skip_fn:
                action = prompt_skip_fn(dir_path, True, str(exc))
                if isinstance(action, bool):
                    action = "skip" if action else "abort"
                if action == "retry":
                    continue
                elif action == "skip":
                    return "skipped"
                else:
                    return "abort"
            return "abort"


def clean_folders(
    folders: List[Path],
    progress_fn: Optional[Callable[[str, int, int], None]] = None,
    prompt_skip_fn: Optional[Callable[[Path, bool, str], str]] = None,
    is_cancelled_fn: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Deletes all files and subdirectories inside the listed folders while keeping
    the root folders intact.

    :param folders: List of Path objects to clean.
    :param progress_fn: Callback(current_path_str, cleaned_count, total_count).
    :param prompt_skip_fn: Callback(item_path, is_dir, error_str) -> str ('retry', 'skip', 'abort').
    :param is_cancelled_fn: Callback() -> bool returning True if cancelled.
    :return: Summary dictionary with results.
    """
    total_items = scan_all_folders(folders)
    cleaned_count = 0
    skipped_count = 0
    cleaned_bytes = 0
    cleaned_folders = []
    cancelled = False

    for folder in folders:
        if is_cancelled_fn and is_cancelled_fn():
            cancelled = True
            break

        if not folder.exists() or not folder.is_dir():
            continue

        folder_cleaned = False

        # Walk bottom-up to delete files first, then directories
        for root, dirs, files in os.walk(folder, topdown=False):
            if is_cancelled_fn and is_cancelled_fn():
                cancelled = True
                break

            # Delete files
            for file_name in files:
                if is_cancelled_fn and is_cancelled_fn():
                    cancelled = True
                    break

                file_path = Path(root) / file_name
                if progress_fn:
                    progress_fn(str(file_path), cleaned_count, total_items)

                status, file_size = delete_single_file(file_path, prompt_skip_fn)
                if status == "deleted":
                    cleaned_count += 1
                    cleaned_bytes += file_size
                    folder_cleaned = True
                elif status == "skipped":
                    skipped_count += 1
                else:
                    # User chose Cancel / Abort
                    skipped_count += 1
                    cancelled = True
                    break

            if cancelled:
                break

            # Delete empty subdirectories (exclude root folder)
            for dir_name in dirs:
                if is_cancelled_fn and is_cancelled_fn():
                    cancelled = True
                    break

                dir_path = Path(root) / dir_name
                if dir_path == folder:
                    continue

                if progress_fn:
                    progress_fn(str(dir_path), cleaned_count, total_items)

                status = delete_single_dir(dir_path, prompt_skip_fn)
                if status == "deleted":
                    cleaned_count += 1
                    folder_cleaned = True
                elif status == "skipped":
                    skipped_count += 1
                else:
                    skipped_count += 1
                    cancelled = True
                    break

            if cancelled:
                break

        if folder_cleaned or folder.exists():
            cleaned_folders.append(str(folder))

        if cancelled:
            break

    # Final progress update
    if progress_fn:
        progress_fn("Complete" if not cancelled else "Cancelled", cleaned_count, total_items)

    return {
        "total_items": total_items,
        "cleaned_count": cleaned_count,
        "skipped_count": skipped_count,
        "cleaned_bytes": cleaned_bytes,
        "cleaned_folders": cleaned_folders,
        "cancelled": cancelled,
    }
