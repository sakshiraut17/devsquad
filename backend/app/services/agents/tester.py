"""SandboxTesterAgent: Executes tests in isolated Docker container or performs safe AST fallback."""

import ast
import asyncio
import io
import logging
import tarfile
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import docker
from docker.errors import DockerException

from app.core.config import settings
from app.core.security import is_safe_relative_path
from app.schemas.patch import PatchItem
from app.schemas.test_result import TestResult
from app.services.agents.diff_utils import apply_unified_diff, split_multi_file_unified_diff
from app.services.health_service import is_docker_available

logger = logging.getLogger("devsquad.tester")

# Whitelist of permissible test execution commands in sandbox
PERMITTED_TEST_COMMAND_PREFIXES = (
    "pytest",
    "python -m pytest",
    "python -m unittest",
    "npm test",
    "npm run test",
    "yarn test",
    "go test",
    "cargo test",
)

SUPPORTED_PYTHON_CONFIGS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "Pipfile",
)


class SandboxTesterAgent:
    """Asynchronous agent that runs test validation in Docker or safe AST fallback."""

    def __init__(self, docker_client: Optional[docker.DockerClient] = None):
        self._docker_client = docker_client

    def _get_docker_client(self) -> Optional[docker.DockerClient]:
        if self._docker_client:
            return self._docker_client
        try:
            return docker.from_env()
        except DockerException:
            return None

    def _detect_project_type(self, files: Dict[str, str]) -> str:
        """Detect project type from repository filenames and extensions."""
        for path in files.keys():
            norm = path.replace("\\", "/")
            base = norm.rsplit("/", 1)[-1]
            if base in SUPPORTED_PYTHON_CONFIGS or base.endswith(".py"):
                return "python"
        return "unsupported"

    async def run_tests(
        self,
        patch: PatchItem,
        source_files: Dict[str, str],
        test_commands: Optional[List[str]] = None,
        required_tests: Optional[List[str]] = None,
        base_image: str = "python:3.11-slim",
        base_commit_sha: Optional[str] = None,
    ) -> TestResult:
        """Run tests either inside an isolated Docker sandbox or via safe host AST fallback."""
        start_time = time.perf_counter()
        commit_sha = base_commit_sha or patch.base_commit_sha

        # 1. Reject empty source files workspace
        if not source_files:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return TestResult(
                status="INVALID_PATCH",
                environment="uninitialized",
                exit_code=1,
                passed=0,
                failed=1,
                skipped=0,
                failure_summary="Empty source repository workspace cannot be tested.",
                patch_hash=patch.content_hash,
                patch_revision=patch.revision,
                base_commit_sha=commit_sha,
                duration_ms=duration_ms,
            )

        # 2. Validate paths and build patched workspace
        patched_files: Dict[str, str] = dict(source_files)
        try:
            per_file_diffs = split_multi_file_unified_diff(patch.unified_diff)
            for tf, fdiff in per_file_diffs.items():
                if not is_safe_relative_path(tf):
                    duration_ms = int((time.perf_counter() - start_time) * 1000)
                    return TestResult(
                        status="INVALID_PATCH",
                        environment="validation_pipeline",
                        exit_code=1,
                        passed=0,
                        failed=1,
                        skipped=0,
                        failure_summary=f"Unsafe relative path '{tf}' in patch rejected.",
                        patch_hash=patch.content_hash,
                        patch_revision=patch.revision,
                        base_commit_sha=commit_sha,
                        duration_ms=duration_ms,
                    )
                orig = patched_files.get(tf, "")
                patched_files[tf] = apply_unified_diff(orig, fdiff)
        except Exception as patch_err:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return TestResult(
                status="INVALID_PATCH",
                environment="validation_pipeline",
                exit_code=1,
                passed=0,
                failed=1,
                skipped=0,
                failure_summary=f"Patch application failed: {str(patch_err)}",
                stderr=str(patch_err),
                patch_hash=patch.content_hash,
                patch_revision=patch.revision,
                base_commit_sha=commit_sha,
                duration_ms=duration_ms,
            )

        # 3. Project type detection
        project_type = self._detect_project_type(patched_files)
        if project_type != "python":
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            return TestResult(
                status="UNSUPPORTED_PROJECT_TYPE",
                environment="validation_pipeline",
                exit_code=1,
                passed=0,
                failed=1,
                skipped=0,
                failure_summary="Unsupported project type: no Python configuration or source files found in workspace.",
                patch_hash=patch.content_hash,
                patch_revision=patch.revision,
                base_commit_sha=commit_sha,
                duration_ms=duration_ms,
            )

        # 4. Check Docker availability
        docker_ready = is_docker_available()
        client = self._get_docker_client() if docker_ready else None

        if client and docker_ready:
            logger.info("Executing tests in Docker sandbox mode with patched workspace.")
            return await self._run_docker_sandbox(
                client=client,
                patch=patch,
                patched_files=patched_files,
                test_commands=test_commands or ["pytest -v"],
                base_image=base_image,
                base_commit_sha=commit_sha,
                start_time=start_time,
            )
        else:
            logger.warning(
                "Docker is unavailable. Executing safe static-validation AST fallback. "
                "No untrusted code will be executed on the host."
            )
            return self._run_static_ast_fallback(
                patch=patch,
                source_files=source_files,
                base_commit_sha=commit_sha,
                start_time=start_time,
            )

    async def _run_docker_sandbox(
        self,
        client: docker.DockerClient,
        patch: PatchItem,
        patched_files: Dict[str, str],
        test_commands: List[str],
        base_image: str,
        base_commit_sha: Optional[str],
        start_time: float,
    ) -> TestResult:
        """Execute test commands inside disposable Docker container with patched workspace and hardened isolation."""
        container = None
        executed_cmds: List[str] = []
        stdout_buf: List[str] = []
        stderr_buf: List[str] = []
        last_exit_code = 0
        status = "TESTS_PASSED"

        # Validate test commands against permitted whitelist
        for cmd in test_commands:
            if not any(cmd.strip().startswith(prefix) for prefix in PERMITTED_TEST_COMMAND_PREFIXES):
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return TestResult(
                    status="REJECTED_UNPERMITTED_COMMAND",
                    environment="docker_container",
                    commands_executed=[],
                    exit_code=1,
                    passed=0,
                    failed=1,
                    skipped=0,
                    stdout="",
                    stderr=f"Command '{cmd}' is not in sandbox permitted test command whitelist.",
                    duration_ms=duration_ms,
                    failure_summary="Unpermitted test command rejected by sandbox security policy.",
                    patch_hash=patch.content_hash,
                    patch_revision=patch.revision,
                    base_commit_sha=base_commit_sha,
                    security_limitations=[
                        "Non-root execution",
                        "Network disabled",
                        "Command whitelisting enforced",
                    ],
                )

        try:
            # Build tarball of patched files with non-root ownership (1000:1000)
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                for rel_path, content in patched_files.items():
                    norm_path = rel_path.lstrip("/").replace("\\", "/")
                    data = content.encode("utf-8")
                    tarinfo = tarfile.TarInfo(name=norm_path)
                    tarinfo.size = len(data)
                    tarinfo.mtime = int(time.time())
                    tarinfo.mode = 0o644
                    tarinfo.uid = 1000
                    tarinfo.gid = 1000
                    tar.addfile(tarinfo, io.BytesIO(data))
            tar_bytes = tar_stream.getvalue()

            # Create isolated container
            nano_cpus = int(settings.docker_cpu_limit * 1e9)
            container = await asyncio.to_thread(
                client.containers.create,
                image=base_image,
                command="/bin/sh -c 'sleep 3600'",
                user="1000:1000",
                network_mode="none",
                mem_limit=settings.docker_memory_limit,
                nano_cpus=nano_cpus,
                pids_limit=100,
                privileged=False,
                volumes={},  # No host mounts, no Docker socket mount
                working_dir="/workspace",
                detach=True,
            )

            # Copy patched workspace into isolated container
            if hasattr(container, "put_archive"):
                await asyncio.to_thread(container.put_archive, path="/workspace", data=tar_bytes)

            await asyncio.to_thread(container.start)

            # Execute test commands inside patched /workspace
            for cmd in test_commands:
                executed_cmds.append(cmd)
                exec_res = await asyncio.wait_for(
                    asyncio.to_thread(
                        container.exec_run,
                        cmd=cmd,
                        workdir="/workspace",
                        user="1000:1000",
                    ),
                    timeout=float(settings.docker_timeout_seconds),
                )
                last_exit_code = exec_res.exit_code
                out = exec_res.output.decode("utf-8", errors="replace") if exec_res.output else ""
                # Bound captured output
                if len(out) > 50_000:
                    out = out[:50_000] + "\n...[OUTPUT TRUNCATED DUE TO SIZE LIMIT]"
                stdout_buf.append(out)

                if last_exit_code != 0:
                    status = "TESTS_FAILED"
                    stderr_buf.append(f"Command '{cmd}' failed with exit code {last_exit_code}")
                    break

        except asyncio.TimeoutError:
            status = "EXECUTION_TIMEOUT"
            last_exit_code = 124
            stderr_buf.append(f"Sandbox execution timed out after {settings.docker_timeout_seconds} seconds.")
        except Exception as exc:
            status = "SANDBOX_ERROR"
            last_exit_code = 1
            stderr_buf.append(f"Docker sandbox error: {str(exc)}")
        finally:
            if container:
                try:
                    await asyncio.to_thread(container.remove, force=True)
                except Exception as clean_err:
                    logger.error(f"Error cleaning up sandbox container: {clean_err}")

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return TestResult(
            status=status,
            environment="docker_container",
            commands_executed=executed_cmds,
            exit_code=last_exit_code,
            passed=1 if status == "TESTS_PASSED" else 0,
            failed=0 if status == "TESTS_PASSED" else 1,
            skipped=0,
            stdout="\n".join(stdout_buf),
            stderr="\n".join(stderr_buf),
            duration_ms=duration_ms,
            failure_summary="Test execution failed" if status != "TESTS_PASSED" else None,
            patch_hash=patch.content_hash,
            patch_revision=patch.revision,
            base_commit_sha=base_commit_sha,
            security_limitations=[
                "Network disabled (network_mode=none)",
                "Non-root execution (user=1000:1000)",
                "No host mounts or docker socket mounts",
                f"Memory limit: {settings.docker_memory_limit}",
                f"CPU limit: {settings.docker_cpu_limit} CPUs",
                f"Timeout: {settings.docker_timeout_seconds}s",
            ],
        )

    def _run_static_ast_fallback(
        self,
        patch: PatchItem,
        source_files: Dict[str, str],
        base_commit_sha: Optional[str],
        start_time: float,
    ) -> TestResult:
        """Perform safe static Python AST parsing and patch validation on host."""
        per_file_diffs = split_multi_file_unified_diff(patch.unified_diff)
        ast_errors: List[str] = []
        validated_files: List[str] = []

        for tf, fdiff in per_file_diffs.items():
            orig_content = source_files.get(tf, "")
            try:
                patched_code = apply_unified_diff(orig_content, fdiff)
                validated_files.append(tf)

                # If Python file, verify AST parses cleanly
                if tf.endswith(".py"):
                    try:
                        ast.parse(patched_code, filename=tf)
                    except SyntaxError as syn_err:
                        ast_errors.append(
                            f"Syntax error in '{tf}' at line {syn_err.lineno}: {syn_err.msg}"
                        )
            except Exception as exc:
                ast_errors.append(f"Patch validation failed for '{tf}': {str(exc)}")

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        if ast_errors:
            return TestResult(
                status="SYNTAX_VALIDATION_FAILED",
                environment="host_ast_fallback",
                commands_executed=["ast.parse(patched_source)"],
                exit_code=1,
                passed=0,
                failed=len(ast_errors),
                skipped=0,
                stdout=f"Validated files before failure: {', '.join(validated_files)}",
                stderr="\n".join(ast_errors),
                duration_ms=duration_ms,
                failure_summary="Syntax or patch application error detected during static AST analysis.",
                patch_hash=patch.content_hash,
                patch_revision=patch.revision,
                base_commit_sha=base_commit_sha or patch.base_commit_sha,
                security_limitations=[
                    "Docker daemon unavailable",
                    "Dynamic test execution skipped to prevent untrusted host execution",
                    "Host AST validation only",
                ],
            )

        # Honest status: PARTIAL_VALIDATION. Never claim TESTS_PASSED for static AST analysis!
        return TestResult(
            status="PARTIAL_VALIDATION",
            environment="host_ast_fallback",
            commands_executed=["ast.parse(patched_source)"],
            exit_code=0,
            passed=len(validated_files),
            failed=0,
            skipped=0,
            stdout=(
                f"Static AST syntax and patch validation passed for {len(validated_files)} file(s): "
                f"{', '.join(validated_files)}. All modified Python files parsed cleanly."
            ),
            stderr="",
            duration_ms=duration_ms,
            failure_summary=None,
            patch_hash=patch.content_hash,
            patch_revision=patch.revision,
            base_commit_sha=base_commit_sha or patch.base_commit_sha,
            security_limitations=[
                "Docker daemon unavailable (SANDBOX_UNAVAILABLE)",
                "Host isolation policy active: dynamic tests were NOT executed on host",
                "AST syntax validity confirmed; full test suite pass NOT verified",
            ],
        )
