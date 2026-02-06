import asyncio
from pathlib import Path
from typing import List, Type, Optional
from pydantic import BaseModel, Field
from .directory_validator import is_path_safe
from .base import ToolBase


class ListDirectoryArgs(BaseModel):
    """Schema for listing directory contents."""
    relative_path: str = Field(
        description=(
            "The relative path of the directory to list. "
            "Use '.' for the workspace root. Do not start with slash."
        )
    )


class ListDirectoryTool(ToolBase):
    """A tool for listing the contents of a directory."""
    name: str = "ListDirectoryTool"
    description: str = (
        "Use this tool to list the files and folders in a specified directory "
        "within the workspace. Provide the relative path to the directory."
    )
    args_schema: Type[BaseModel] = ListDirectoryArgs
    working_directory: Path = Path.cwd()

    # ------------------------------------------------------------------
    # LangChain entry points
    # ------------------------------------------------------------------

    def _run(self, relative_path: str) -> str:
        self.logger.debug(f"[ListDirectoryTool] Listing directory (sync): {relative_path}")
        return self._execute_sync(relative_path)

    async def _arun(self, relative_path: str) -> str:
        self.logger.debug(f"[ListDirectoryTool] Listing directory (async): {relative_path}")
        return await self._execute_async(relative_path)

    # ------------------------------------------------------------------
    # Execution paths
    # ------------------------------------------------------------------

    def _execute_sync(self, relative_path: str) -> str:
        is_safe, resolved_path = is_path_safe(self.working_directory, relative_path)

        if resolved_path is None:
            return f"Unsafe or invalid path provided: {relative_path}. Always use paths relative to the working directory."

        error = self._validate_path(is_safe, resolved_path, relative_path)
        if error:
            return error

        try:
            contents = list(resolved_path.iterdir())
        except PermissionError:
            return f"Error: Permission denied for accessing the directory at '{relative_path}'."
        except Exception as e:
            return f"An unexpected error occurred while accessing '{relative_path}': {e}"

        return self._format_output(contents, resolved_path)

    async def _execute_async(self, relative_path: str) -> str:
        is_safe, resolved_path = is_path_safe(self.working_directory, relative_path)
        if resolved_path is None:
            return f"Unsafe or invalid path provided: {relative_path}. Always use paths relative to the working directory."
        error = self._validate_path(is_safe, resolved_path, relative_path)
        if error:
            return error

        try:
            contents = await asyncio.to_thread(lambda: list(resolved_path.iterdir()))
        except PermissionError:
            return f"Error: Permission denied for accessing the directory at '{relative_path}'."
        except Exception as e:
            return f"An unexpected error occurred while accessing '{relative_path}': {e}"

        return self._format_output(contents, resolved_path)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_path(
        self,
        is_safe: bool,
        resolved_path: Optional[Path],
        relative_path: str,
    ) -> Optional[str]:
        if not is_safe or resolved_path is None:
            return (
                f"Unsafe or invalid path provided: {relative_path}. "
                f"Always use paths relative to the working directory."
            )

        if not resolved_path.exists():
            return f"Error: Path '{relative_path}' does not exist."

        if not resolved_path.is_dir():
            return (
                f"Error: The path '{relative_path}' points to a file, "
                f"not a directory. Cannot list contents."
            )

        return None

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def _format_output(self, contents: List[Path], resolved_path: Path) -> str:
        # Exclude hidden files/folders
        contents = [p for p in contents if not p.name.startswith(".")]

        if not contents:
            return f"The directory '{resolved_path.relative_to(self.working_directory)}' is currently empty."

        directories = sorted(p.name for p in contents if p.is_dir())
        files = sorted(p.name for p in contents if p.is_file())

        output = [
            f"The directory **{resolved_path.relative_to(self.working_directory)}** "
            f"contains the following items:"
        ]

        if directories:
            output.append(
                f"  - **{len(directories)} directories** including: {', '.join(directories)}."
            )

        if files:
            output.append(
                f"  - **{len(files)} files** including: {', '.join(files)}."
            )

        return "\n".join(output)
