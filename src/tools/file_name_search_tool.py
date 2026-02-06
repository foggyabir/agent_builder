import asyncio
import fnmatch
from pathlib import Path
from typing import Optional, Type, List
from pydantic import BaseModel, Field
from .directory_validator import is_path_safe
from .base import ToolBase


class FileNameSearchArgs(BaseModel):
    """Schema for searching files by name using glob patterns."""
    pattern: str = Field(
        ...,
        description=(
            "File name or glob pattern to search for. "
            "Examples: 'app.module.ts', '*.module.ts', '**/*routing.module.ts'"
        )
    )
    relative_path: str = Field(
        ".",
        description="Relative directory path to limit the search scope. Defaults to workspace root."
    )


class FileNameSearchTool(ToolBase):
    """
    Tool for locating files in the workspace by name using glob-style patterns.
    """
    name: str = "FileNameSearchTool"
    description: str = (
        "Searches the workspace for files matching a given file name or glob pattern. "
        "Returns matching file paths relative to the workspace root. "
        "Supports wildcards such as '*', '**', and '?' (glob syntax). "
        "Maximum number of results returned is 100. If exceeded, results are truncated with a warning."
    )
    args_schema: Type[BaseModel] = FileNameSearchArgs

    working_directory: Path = Path.cwd()
    max_results: int = 100

    # ------------------------------------------------------------------
    # LangChain entry points
    # ------------------------------------------------------------------

    def _run(self, pattern: str, relative_path: str = ".") -> str:
        self.logger.debug(
            f"[FileNameSearchTool] Searching (sync) for '{pattern}' "
            f"in '{relative_path}'"
        )
        return self._execute_sync(pattern, relative_path)

    async def _arun(self, pattern: str, relative_path: str = ".") -> str:
        self.logger.debug(
            f"[FileNameSearchTool] Searching (async) for '{pattern}' "
            f"in '{relative_path}'"
        )
        return await self._execute_async(pattern, relative_path)

    # ------------------------------------------------------------------
    # Execution paths
    # ------------------------------------------------------------------

    def _execute_sync(self, pattern: str, relative_path: str) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"ERROR: The search path '{relative_path}' is outside the authorized workspace."

        error = self._validate_path(is_safe, target_path, relative_path)
        if error:
            return error

        try:
            matched_files, truncated = self._search_files(target_path, pattern)
        except Exception as e:
            return f"ERROR: An unexpected error occurred: {e}"

        return self._format_output(matched_files, truncated, pattern, relative_path)

    async def _execute_async(self, pattern: str, relative_path: str) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"ERROR: The search path '{relative_path}' is outside the authorized workspace."
        error = self._validate_path(is_safe, target_path, relative_path)
        if error:
            return error

        try:
            matched_files, truncated = await asyncio.to_thread(
                self._search_files, target_path, pattern
            )
        except Exception as e:
            return f"ERROR: An unexpected error occurred: {e}"

        return self._format_output(matched_files, truncated, pattern, relative_path)

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

        if not target_path.is_dir():
            return f"ERROR: The search path '{relative_path}' is not a directory."

        return None

    # ------------------------------------------------------------------
    # Core search logic (shared)
    # ------------------------------------------------------------------

    def _search_files(self, target_path: Path, pattern: str) -> tuple[List[str], bool]:
        matched_files: List[str] = []
        truncated = False

        for path in target_path.rglob("*"):
            if not path.is_file():
                continue

            relative_file = path.relative_to(self.working_directory)

            if (
                fnmatch.fnmatch(path.name, pattern)
                or fnmatch.fnmatch(str(relative_file), pattern)
            ):
                matched_files.append(str(relative_file))

            if len(matched_files) >= self.max_results:
                truncated = True
                break

        return matched_files, truncated

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    def _format_output(
        self,
        matched_files: List[str],
        truncated: bool,
        pattern: str,
        relative_path: str,
    ) -> str:
        if not matched_files:
            return (
                f"No files found matching pattern '{pattern}' "
                f"in '{relative_path}'."
            )

        output_body = "\n".join(matched_files)

        if truncated:
            return (
                f"File search results for pattern '{pattern}' (TRUNCATED):\n\n"
                f"{output_body}\n\n"
                f"--- LIMIT REACHED ---\n"
                f"WARNING: Only the first {self.max_results} matches are shown.\n"
                f"ADVICE: Narrow your pattern or restrict the search path."
            )

        return f"File search results for pattern '{pattern}':\n\n{output_body}"
