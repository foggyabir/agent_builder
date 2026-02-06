import aiofiles
from pathlib import Path
from typing import Type, Optional
from pydantic import BaseModel, Field
from .directory_validator import is_path_safe
from .base import ToolBase


class WriteFileArgs(BaseModel):
    """Schema for writing content to a file."""
    relative_path: str = Field(
        ...,
        description=(
            "The relative path where the file should be written. "
            "Directories will be created if they don't exist."
        )
    )
    content: str = Field(
        ...,
        description="The full text content to write into the file."
    )


class WriteFileTool(ToolBase):
    """A tool for writing content to a file."""
    name: str = "WriteFileTool"
    description: str = (
        "Use this tool to write content to a file within the workspace. "
        "You must provide the relative path and the content to write."
    )
    args_schema: Type[BaseModel] = WriteFileArgs

    working_directory: Path = Path.cwd()

    # ------------------------------------------------------------------
    # LangChain entry points
    # ------------------------------------------------------------------

    def _run(self, relative_path: str, content: str) -> str:
        self.logger.debug(f"[WriteFileTool] Writing file (sync): {relative_path}")
        return self._execute_sync(relative_path, content)

    async def _arun(self, relative_path: str, content: str) -> str:
        self.logger.debug(f"[WriteFileTool] Writing file (async): {relative_path}")
        return await self._execute_async(relative_path, content)

    # ------------------------------------------------------------------
    # Execution paths
    # ------------------------------------------------------------------

    def _execute_sync(self, relative_path: str, content: str) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"Unsafe or invalid path provided: {relative_path}. Always use paths relative to the working directory."
        error = self._validate_target(is_safe, target_path, relative_path)
        if error:
            return error

        error = self._ensure_parent_dir(target_path, relative_path)
        if error:
            return error

        try:
            target_path.write_text(content, encoding="utf-8")
            return self._success_message(relative_path, content)
        except PermissionError:
            return f"ERROR: Permission denied for writing to file '{relative_path}'."
        except Exception as e:
            return f"ERROR: An unexpected error occurred while writing '{relative_path}': {e}"

    async def _execute_async(self, relative_path: str, content: str) -> str:
        is_safe, target_path = is_path_safe(self.working_directory, relative_path)
        if target_path is None:
            return f"Unsafe or invalid path provided: {relative_path}. Always use paths relative to the working directory."
        error = self._validate_target(is_safe, target_path, relative_path)
        if error:
            return error

        error = self._ensure_parent_dir(target_path, relative_path)
        if error:
            return error

        try:
            async with aiofiles.open(target_path, "w", encoding="utf-8") as f:
                await f.write(content)
            return self._success_message(relative_path, content)
        except PermissionError:
            return f"ERROR: Permission denied for writing to file '{relative_path}'."
        except Exception as e:
            return f"ERROR: An unexpected error occurred while writing '{relative_path}': {e}"

    # ------------------------------------------------------------------
    # Validation & directory handling
    # ------------------------------------------------------------------

    def _validate_target(
        self,
        is_safe: bool,
        target_path: Optional[Path],
        relative_path: str,
    ) -> Optional[str]:
        if not is_safe or target_path is None:
            return (
                f"ERROR: The target path '{relative_path}' is outside the "
                f"authorized workspace or is not valid. Write operation denied."
            )

        if target_path.exists() and target_path.is_dir():
            return (
                f"ERROR: The target path '{relative_path}' is a directory. "
                f"Cannot write content to a directory."
            )

        return None

    def _ensure_parent_dir(
        self,
        target_path: Path,
        relative_path: str,
    ) -> Optional[str]:
        parent_dir = target_path.parent

        if parent_dir.exists():
            return None

        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
            return None
        except PermissionError:
            return (
                f"ERROR: Permission denied for creating the directory structure "
                f"for '{relative_path}'."
            )
        except Exception as e:
            return (
                f"ERROR: Failed to create parent directories for "
                f"'{relative_path}': {e}"
            )

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def _success_message(self, relative_path: str, content: str) -> str:
        return (
            f"SUCCESS: Content successfully written to file "
            f"**{relative_path}**. "
            f"Total characters written: {len(content)}."
        )
