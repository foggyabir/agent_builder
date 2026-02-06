import aiofiles
from pathlib import Path
from typing import Optional, Type, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from .directory_validator import is_path_safe
from .base import ToolBase


class ReadFileArgs(BaseModel):
    """Schema for reading file contents with pagination."""
    relative_path: str = Field(
        ...,
        description="The relative path of the file to read."
    )
    offset: int = Field(
        1,
        description="The line number to start reading from (1-indexed). Defaults to 1."
    )
    limit: Optional[int] = Field(
        None,
        description="Maximum number of lines to read."
    )


class ReadFileTool(ToolBase):
    """A tool for reading the contents of a file with pagination."""
    name: str = "ReadFileTool"
    description: str = (
        "Use this tool to read the contents of a file within the workspace. "
        "You can specify the relative path, offset, and limit for pagination.\n"
        "To read a file fully do not pass any limit.\n"
        "Returns the file content with line numbers for easy reference."
    )
    args_schema: Type[BaseModel] = ReadFileArgs
    working_directory: Path = Path.cwd()

    # ------------------------------------------------------------------
    # Public LangChain hooks
    # ------------------------------------------------------------------

    def _run(self, relative_path: str, offset: int = 1, limit: Optional[int] = None) -> str:
        self.logger.debug(f"[ReadFileTool] Reading file (sync): {relative_path} with offset {offset} and limit {limit}")
        return self._execute_sync(relative_path, offset, limit)

    async def _arun(self, relative_path: str, offset: int = 1, limit: Optional[int] = None) -> str:
        self.logger.debug(f"[ReadFileTool] Reading file (async): {relative_path} with offset {offset} and limit {limit}")
        return await self._execute_async(relative_path, offset, limit)

    # ------------------------------------------------------------------
    # Core execution pipeline (shared)
    # ------------------------------------------------------------------


    def _execute_sync(self, relative_path: str, offset: int, limit: Optional[int]) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"Unsafe or invalid path provided: {relative_path}. Always use paths relative to the working directory."
        error = self._validate_path(is_safe, target_path, relative_path, offset)
        if error:
            return error

        try:
            lines = self._read_lines_sync(target_path)
        except Exception as e:
            return f"ERROR: An unexpected error occurred while reading '{relative_path}': {e}"

        return self._process_lines(lines, target_path, relative_path, offset, limit)

    async def _execute_async(self, relative_path: str, offset: int, limit: Optional[int]) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"Unsafe or invalid path provided: {relative_path}. Always use paths relative to the working directory."
        error = self._validate_path(is_safe, target_path, relative_path, offset)
        if error:
            return error

        try:
            lines = await self._read_lines_async(target_path)
        except Exception as e:
            return f"ERROR: An unexpected error occurred while reading '{relative_path}': {e}"

        return self._process_lines(lines, target_path, relative_path, offset, limit)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_path(
        self,
        is_safe: bool,
        target_path: Optional[Path],
        relative_path: str,
        offset: int,
    ) -> Optional[str]:
        if not is_safe or target_path is None:
            return (
                f"ERROR: The path '{relative_path}' is outside the authorized "
                f"workspace or is not valid. Content access denied."
            )

        if not target_path.exists():
            return f"ERROR: File not found at path '{relative_path}'."

        if not target_path.is_file():
            return (
                f"ERROR: The path '{relative_path}' points to a directory, "
                f"not a file. Cannot read content."
            )

        if offset < 1:
            return f"ERROR: Offset must be 1 or greater, but received {offset}."

        return None

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    def _read_lines_sync(self, path: Path) -> List[str]:
        try:
            return path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1").splitlines()

    async def _read_lines_async(self, path: Path) -> List[str]:
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                content = await f.read()
        except UnicodeDecodeError:
            async with aiofiles.open(path, "r", encoding="latin-1") as f:
                content = await f.read()

        return content.splitlines()

    # ------------------------------------------------------------------
    # Line slicing + formatting
    # ------------------------------------------------------------------

    def _process_lines(
        self,
        lines: List[str],
        target_path: Path,
        relative_path: str,
        offset: int,
        limit: Optional[int],
    ) -> str:
        total_lines = len(lines)
        start_index = offset - 1

        if start_index >= total_lines:
            return (
                f"ERROR: Offset line {offset} is greater than the total number "
                f"of lines ({total_lines}) in the file."
            )

        end_index = total_lines if limit is None else min(start_index + limit, total_lines)
        lines_to_output = lines[start_index:end_index]

        start_line = start_index + 1
        end_line = end_index

        header = (
            f"--- START OF FILE CONTENT FOR '{target_path.name}' "
            f"(Lines {start_line}-{end_line} of {total_lines}, "
            f"Path: {relative_path}) ---"
        )
        footer = "--- END OF FILE CONTENT ---"

        return f"{header}\n{'\n'.join(lines_to_output)}\n{footer}"
