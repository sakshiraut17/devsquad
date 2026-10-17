"""Unit tests for pure Python unified diff utilities."""

import pytest
from app.services.agents.diff_utils import (
    PatchError,
    PatchHunkMismatchError,
    apply_unified_diff,
    parse_unified_diff_files,
    split_multi_file_unified_diff,
    validate_unified_diff_safety,
)


def test_parse_unified_diff_files():
    diff_text = """diff --git a/app/core/auth.py b/app/core/auth.py
--- a/app/core/auth.py
+++ b/app/core/auth.py
@@ -1,3 +1,3 @@
-old line
+new line
"""
    files = parse_unified_diff_files(diff_text)
    assert files == [("app/core/auth.py", "app/core/auth.py")]


def test_validate_unified_diff_safety_rejects_traversal():
    traversal_diff = """--- a/../../etc/passwd
+++ b/../../etc/passwd
@@ -1,1 +1,1 @@
-root
+hacked
"""
    with pytest.raises(PatchError) as exc:
        validate_unified_diff_safety(traversal_diff)
    assert "Unsafe path detected" in str(exc.value)


def test_validate_unified_diff_safety_rejects_absolute_path():
    abs_diff = """--- C:/Windows/System32/drivers/etc/hosts
+++ C:/Windows/System32/drivers/etc/hosts
@@ -1,1 +1,1 @@
-localhost
+attacker
"""
    with pytest.raises(PatchError) as exc:
        validate_unified_diff_safety(abs_diff)
    assert "Unsafe path detected" in str(exc.value)


def test_apply_unified_diff_success():
    original = "def add(a, b):\n    return a - b\n"
    diff = """--- a/math_ops.py
+++ b/math_ops.py
@@ -1,2 +1,2 @@
 def add(a, b):\n-    return a - b
+    return a + b
"""
    patched = apply_unified_diff(original, diff)
    assert patched == "def add(a, b):\n    return a + b\n"


def test_apply_unified_diff_hunk_mismatch():
    original = "def multiply(a, b):\n    return a * b\n"
    diff = """--- a/math_ops.py
+++ b/math_ops.py
@@ -1,2 +1,2 @@
 def add(a, b):\n-    return a - b
+    return a + b
"""
    with pytest.raises(PatchHunkMismatchError):
        apply_unified_diff(original, diff)


def test_split_multi_file_unified_diff():
    multi_diff = """diff --git a/file1.py b/file1.py
--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,1 @@
-one
+ONE
diff --git a/file2.py b/file2.py
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,1 @@
-two
+TWO
"""
    splits = split_multi_file_unified_diff(multi_diff)
    assert "file1.py" in splits
    assert "file2.py" in splits
