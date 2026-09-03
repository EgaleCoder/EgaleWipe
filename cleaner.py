import os
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Dict, Any


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
    prompt_skip_fn: Optional[Callable[[str, str], bool]] = None,
) -> bool:
    """
    Attempts to delete a single file.
    If deletion fails, calls prompt_skip_fn(file_name, error_message).
    Returns True if deleted or skipped (to continue), False to abort.
    """
    try:
        # If file is read-only on Windows, remove read-only attribute
        if not os.access(file_path, os.W_OK):
            os.chmod(file_path, 0o777)
        file_path.unlink()
        return True
    except Exception as exc:
        if prompt_skip_fn:
            should_skip = prompt_skip_fn(file_path.name, str(exc))
            return should_skip
        return False


def delete_single_dir(
    dir_path: Path,
    prompt_skip_fn: Optional[Callable[[str, str], bool]] = None,
) -> bool:
    """Attempts to remove an empty directory."""
    try:
        dir_path.rmdir()
        return True
    except Exception as exc:
        if prompt_skip_fn:
            return prompt_skip_fn(dir_path.name, str(exc))
        return False


def clean_folders(
    folders: List[Path],
    progress_fn: Optional[Callable[[str, int, int], None]] = None,
    prompt_skip_fn: Optional[Callable[[str, str], bool]] = None,
    is_cancelled_fn: Optional[Callable[[], bool]] = None,
) -> Dict[str, Any]:
    """
    Deletes all files and subdirectories inside the listed folders while keeping
    the root folders intact.

    :param folders: List of Path objects to clean.
    :param progress_fn: Callback(current_path_str, cleaned_count, total_count).
    :param prompt_skip_fn: Callback(item_name, error_str) -> bool (True=Skip, False=Abort).
    :param is_cancelled_fn: Callback() -> bool returning True if cancelled.
    :return: Summary dictionary with results.
    """
    total_items = scan_all_folders(folders)
    cleaned_count = 0
    skipped_count = 0
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

                success = delete_single_file(file_path, prompt_skip_fn)
                if success:
                    cleaned_count += 1
                    folder_cleaned = True
                else:
                    # User chose 'No' on prompt (Abort) or unhandled error
                    skipped_count += 1
                    if prompt_skip_fn:
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

                success = delete_single_dir(dir_path, prompt_skip_fn)
                if success:
                    cleaned_count += 1
                    folder_cleaned = True
                else:
                    skipped_count += 1
                    if prompt_skip_fn:
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
        "cleaned_folders": cleaned_folders,
        "cancelled": cancelled,
    }
