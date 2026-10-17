"""Pure Python unified diff parsing, validation, and safe application utilities.

Enables cross-platform, deterministic patch verification without external
CLI dependencies (git, patch) and enforces strict path-traversal safety.
"""

import re
from typing import Dict, List, Tuple
from app.core.exceptions import ValidationError
from app.core.security import is_safe_relative_path


class PatchError(ValidationError):
    """Raised when patch parsing, safety validation, or application fails."""
    pass


class PatchHunkMismatchError(PatchError):
    """Raised when context lines in a diff hunk do not match the target source file."""
    pass


def parse_unified_diff_files(diff_text: str) -> List[Tuple[str, str]]:
    """Extract (old_path, new_path) tuples from unified diff headers.
    
    Handles standard formats:
    --- a/path/to/file.py
    +++ b/path/to/file.py
    or
    --- path/to/file.py
    +++ path/to/file.py
    """
    file_pairs: List[Tuple[str, str]] = []
    old_file = None

    for line in diff_text.splitlines():
        if line.startswith("--- "):
            raw = line[4:].strip().split("\t")[0]
            if raw.startswith("a/"):
                raw = raw[2:]
            elif raw == "/dev/null":
                raw = "/dev/null"
            old_file = raw
        elif line.startswith("+++ ") and old_file is not None:
            raw = line[4:].strip().split("\t")[0]
            if raw.startswith("b/"):
                raw = raw[2:]
            elif raw == "/dev/null":
                raw = "/dev/null"
            file_pairs.append((old_file, raw))
            old_file = None

    return file_pairs


def validate_unified_diff_safety(diff_text: str) -> List[str]:
    """Validate that all target paths in diff are safe relative paths.
    
    Returns a list of target file paths modified or created.
    Raises PatchError if path traversal or absolute paths are detected.
    """
    if not diff_text or not diff_text.strip():
        raise PatchError("Unified diff is empty.")

    file_pairs = parse_unified_diff_files(diff_text)
    if not file_pairs:
        raise PatchError("No valid unified diff file headers (--- and +++) found in patch.")

    target_paths: List[str] = []
    for old_path, new_path in file_pairs:
        # Check old_path if not newly created file
        if old_path != "/dev/null":
            if not is_safe_relative_path(old_path):
                raise PatchError(f"Unsafe path detected in patch source: '{old_path}'")
        # Check new_path if not deleted file
        if new_path != "/dev/null":
            if not is_safe_relative_path(new_path):
                raise PatchError(f"Unsafe path detected in patch target: '{new_path}'")
            target_paths.append(new_path)
        else:
            target_paths.append(old_path)

    return target_paths


def apply_unified_diff(original_text: str, diff_text: str) -> str:
    """Apply a unified diff targeting a single file to original_text.
    
    Parses unified diff hunks (@@ -start,len +start,len @@) and replaces context.
    Raises PatchHunkMismatchError if hunk context does not match original_text.
    """
    orig_lines = original_text.splitlines(keepends=True)
    # Ensure all lines have newline endings for uniform matching
    orig_lines = [l if l.endswith("\n") else l + "\n" for l in orig_lines]

    hunk_regex = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
    diff_lines = diff_text.splitlines()

    hunks: List[Tuple[int, int, int, int, List[str]]] = []
    current_hunk_lines: List[str] = []
    current_header = None

    for line in diff_lines:
        match = hunk_regex.match(line)
        if match:
            if current_header and current_hunk_lines:
                hunks.append((*current_header, current_hunk_lines))
                current_hunk_lines = []
            old_start = int(match.group(1))
            old_len = int(match.group(2)) if match.group(2) is not None else 1
            new_start = int(match.group(3))
            new_len = int(match.group(4)) if match.group(4) is not None else 1
            current_header = (old_start, old_len, new_start, new_len)
        elif current_header is not None:
            # Diff content lines
            if line.startswith(("+", "-", " ", "\\")):
                current_hunk_lines.append(line)

    if current_header and current_hunk_lines:
        hunks.append((*current_header, current_hunk_lines))

    if not hunks:
        # If no hunks found, return original_text if diff was trivial or error
        raise PatchError("Unified diff contained no valid hunk headers (@@ -x,y +a,b @@).")

    result_lines = list(orig_lines)
    offset = 0

    for old_start, old_len, new_start, new_len, hunk_lines in hunks:
        # Convert 1-based line numbers to 0-based index
        # When old_start == 0 (e.g. empty file creation), index is 0
        idx = max(0, old_start - 1) + offset

        # Separate hunk lines into expected context/remove lines and new lines
        hunk_old: List[str] = []
        hunk_new: List[str] = []

        for hline in hunk_lines:
            if hline.startswith(" "):
                line_content = hline[1:] + "\n"
                hunk_old.append(line_content)
                hunk_new.append(line_content)
            elif hline.startswith("-"):
                line_content = hline[1:] + "\n"
                hunk_old.append(line_content)
            elif hline.startswith("+"):
                line_content = hline[1:] + "\n"
                hunk_new.append(line_content)
            # Ignore '\ No newline at end of file'

        # Verify old lines match expected content in result_lines
        actual_old = result_lines[idx : idx + len(hunk_old)]
        # Normalize trailing whitespace on lines for resilience against CRLF
        actual_normalized = [l.rstrip("\r\n") for l in actual_old]
        expected_normalized = [l.rstrip("\r\n") for l in hunk_old]

        if actual_normalized != expected_normalized:
            raise PatchHunkMismatchError(
                f"Patch hunk at line {old_start} failed to apply: expected {len(expected_normalized)} lines "
                f"but found mismatch in target content.\n"
                f"Expected: {expected_normalized[:3]}\nActual: {actual_normalized[:3]}"
            )

        # Replace slice in result_lines
        result_lines[idx : idx + len(hunk_old)] = hunk_new
        offset += len(hunk_new) - len(hunk_old)

    return "".join(result_lines)


def split_multi_file_unified_diff(diff_text: str) -> Dict[str, str]:
    """Split a multi-file unified diff into a dict mapping target_path -> per-file diff."""
    file_diffs: Dict[str, List[str]] = {}
    current_target = None
    current_lines: List[str] = []

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            if current_target and current_lines:
                file_diffs[current_target] = "\n".join(current_lines) + "\n"
                current_lines = []
            parts = line.split()
            # diff --git a/path b/path
            if len(parts) >= 4 and parts[3].startswith("b/"):
                current_target = parts[3][2:]
            elif len(parts) >= 4:
                current_target = parts[3]
            current_lines.append(line)
        elif line.startswith("+++ ") and not current_target:
            raw = line[4:].strip().split("\t")[0]
            if raw.startswith("b/"):
                raw = raw[2:]
            current_target = raw
            current_lines.append(line)
        else:
            if current_target:
                current_lines.append(line)

    if current_target and current_lines:
        file_diffs[current_target] = "\n".join(current_lines) + "\n"

    # If diff --git was not used, fall back to parsing by +++
    if not file_diffs:
        file_pairs = parse_unified_diff_files(diff_text)
        if len(file_pairs) == 1:
            target = file_pairs[0][1] if file_pairs[0][1] != "/dev/null" else file_pairs[0][0]
            file_diffs[target] = diff_text

    return file_diffs


def canonicalize_unified_diff(diff_text: str) -> str:
    """
    Produce a deterministic, canonical representation of a unified diff.
    - Normalizes line endings (\\r\\n -> \\n)
    - Strips trailing whitespace from each line
    - Trims leading and trailing blank lines while preserving internal hunk structure
    - Ensures a single consistent trailing newline
    """
    if not diff_text or not diff_text.strip():
        return ""
    lines = [line.rstrip() for line in diff_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


def compute_canonical_patch_hash(diff_text: str) -> str:
    """Compute deterministic SHA-256 hash of a normalized canonical unified diff."""
    from app.core.security import compute_sha256
    canonical = canonicalize_unified_diff(diff_text)
    return compute_sha256(canonical)


def compute_canonical_patch_id(base_commit_sha: str, diff_text: str) -> str:
    """
    Compute unique composite canonical patch identity binding the diff to its exact base revision.
    Format: '<base_commit_sha>:<canonical_patch_hash>'
    """
    patch_hash = compute_canonical_patch_hash(diff_text)
    clean_sha = base_commit_sha.strip().lower()
    return f"{clean_sha}:{patch_hash}"
