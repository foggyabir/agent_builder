import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Type, List, Tuple
from pydantic import BaseModel, Field
from utils import is_path_safe
from .base import ToolBase


class SearchArgs(BaseModel):
    """Schema for semantic/regex searching within the workspace."""
    pattern: str = Field(
        ...,
        description="The regular expression or text pattern to search for."
    )
    relative_path: str = Field(
        ".",
        description="The relative directory path to limit the search scope. Defaults to workspace root."
    )
    glob_pattern: Optional[str] = Field(
        None,
        description="A glob pattern to filter files by name or extension (e.g., '*.py', '*.js', '!test_*')."
    )


class SearchWorkspaceWithRipgrepTool(ToolBase):
    """A tool for searching any string in the workspace using ripgrep."""
    name: str = "SearchWorkspaceWithRipgrepTool"
    description: str = (
        "Searches the workspace using ripgrep to find all occurrences of a text or regex pattern. "
        "Returns matches in the format: <FILENAME:LINE_NUMBER:CONTENT>. "
        "Maximum number of results is 100; output is truncated with a warning if exceeded."
    )
    args_schema: Type[BaseModel] = SearchArgs

    working_directory: Path = Path.cwd()
    rg_path: Path = Path("rg")
    max_results: int = 100

    # ------------------------------------------------------------------
    # LangChain entry points
    # ------------------------------------------------------------------

    def _run(
        self,
        pattern: str,
        relative_path: str = ".",
        glob_pattern: Optional[str] = None,
    ) -> str:
        self.logger.debug(f"[SearchWorkspaceWithRipgrepTool] Searching (sync): '{pattern}'")
        return self._execute_sync(pattern, relative_path, glob_pattern)

    async def _arun(
        self,
        pattern: str,
        relative_path: str = ".",
        glob_pattern: Optional[str] = None,
    ) -> str:
        self.logger.debug(f"[SearchWorkspaceWithRipgrepTool] Searching (async): '{pattern}'")
        return await self._execute_async(pattern, relative_path, glob_pattern)

    # ------------------------------------------------------------------
    # Execution paths
    # ------------------------------------------------------------------

    def _execute_sync(
        self,
        pattern: str,
        relative_path: str,
        glob_pattern: Optional[str],
    ) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"ERROR: The search path '{relative_path}' is outside the authorized workspace."
        error = self._validate_path(is_safe, target_path, relative_path)
        if error:
            return error

        try:
            results, truncated, count = self._run_ripgrep(
                pattern, target_path, glob_pattern
            )
        except Exception as e:
            return f"ERROR: An unexpected error occurred: {e}"

        return self._format_output(
            results, truncated, count, pattern, relative_path, glob_pattern
        )

    async def _execute_async(
        self,
        pattern: str,
        relative_path: str,
        glob_pattern: Optional[str],
    ) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"ERROR: The search path '{relative_path}' is outside the authorized workspace."
        error = self._validate_path(is_safe, target_path, relative_path)
        if error:
            return error

        try:
            results, truncated, count = await asyncio.to_thread(
                self._run_ripgrep, pattern, target_path, glob_pattern
            )
        except Exception as e:
            return f"ERROR: An unexpected error occurred: {e}"

        return self._format_output(
            results, truncated, count, pattern, relative_path, glob_pattern
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_path(
        self,
        is_safe: bool,
        target_path: Optional[Path],
        relative_path: str,
    ) -> Optional[str]:
        if not is_safe or target_path is None:
            return f"ERROR: The search path '{relative_path}' is outside the authorized workspace."

        if not target_path.exists():
            return f"ERROR: The search path '{relative_path}' does not exist."

        return None

    # ------------------------------------------------------------------
    # Ripgrep execution (shared)
    # ------------------------------------------------------------------

    def _run_ripgrep(
        self,
        pattern: str,
        target_path: Path,
        glob_pattern: Optional[str],
    ) -> Tuple[List[str], bool, int]:
        command = [
            self.rg_path,
            "--line-number",
            "--color", "never",
            "--no-heading",
            "--with-filename",
            "--smart-case",
            "--max-columns", "300",
            "-e", pattern,
        ]

        if glob_pattern:
            command.extend(["--glob", glob_pattern])

        command.append(str(target_path))

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
        )

        formatted_lines: List[str] = []
        count = 0
        truncated = False

        if process.stdout:
            for line in process.stdout:
                count += 1
                if count <= self.max_results:
                    clean_line = (
                        line.strip()
                        .replace(str(self.working_directory), "")
                        .lstrip("/\\")
                    )
                    formatted_lines.append(clean_line)
                else:
                    truncated = True
                    process.terminate()
                    break

        process.wait()
        process.terminate()

        return formatted_lines, truncated, count

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def _format_output(
        self,
        results: List[str],
        truncated: bool,
        count: int,
        pattern: str,
        relative_path: str,
        glob_pattern: Optional[str],
    ) -> str:
        if count == 0:
            msg = f"No matches found for pattern '{pattern}' in '{relative_path}'"
            if glob_pattern:
                msg += f" matching files '{glob_pattern}'"
            return msg + "."

        output_body = "\n".join(results)

        if truncated:
            return (
                f"Search results for pattern '{pattern}' (TRUNCATED):\n"
                f"{output_body}\n\n"
                f"--- LIMIT REACHED ---\n"
                f"WARNING: Too many results! Only the first {self.max_results} matches are shown.\n"
                f"ADVICE: Refine your search. You used glob: '{glob_pattern}'. Try a more specific folder."
            )

        return f"Search results for pattern '{pattern}':\n\n{output_body}"
