import os
import re
import fnmatch
import shutil
import asyncio
from pathlib import Path
from uuid import uuid4

import aiofiles

from .base import UtilBase
from .models import (
    ProcessedFileDTO,
    UnProcessedFileDTO,
)


class FilePreprocessor(UtilBase):
    def __init__(
        self,
        source_dir,
        target_dir,
        output_subdir: str = "legacy_source",
        max_size_kb=None,
        file_ignore_patterns=None,
        dir_ignore_patterns=None,
        use_gitignore=True,
        max_concurrency: int = 8,
    ):
        super().__init__()

        self.source_dir = Path(source_dir).resolve()
        self.target_dir = Path(target_dir).resolve()

        self.output_subdir = output_subdir
        self.logger.info(f"Target_directory: {self.target_dir}")
        self.output_root = self.target_dir / self.output_subdir

        self.max_size_bytes = (max_size_kb * 1024) if max_size_kb else None
        self.file_ignore_patterns = file_ignore_patterns or []
        self.dir_ignore_patterns = dir_ignore_patterns or []

        self.blob_pattern = re.compile(
            r"(0x[0-9a-fA-F]{500,}|X'[0-9a-fA-F]{500,}')",
            re.IGNORECASE,
        )

        self.semaphore = asyncio.Semaphore(max_concurrency)

        if use_gitignore:
            self._load_gitignore()

    # -------------------------------------------------
    # Helpers (sync)
    # -------------------------------------------------

    def _load_gitignore(self) -> None:
        gitignore_path = self.source_dir / ".gitignore"
        if not gitignore_path.exists():
            return

        try:
            for line in gitignore_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                clean = line.rstrip("/")
                if line.endswith("/"):
                    self.dir_ignore_patterns.append(clean)
                else:
                    self.file_ignore_patterns.append(clean)
        except Exception as e:
            self.logger.warning(f"Could not read .gitignore: {e}")

    def _should_ignore_dir(self, path: Path) -> bool:
        return any(fnmatch.fnmatch(path.name, p) for p in self.dir_ignore_patterns)

    def _should_ignore_file(self, path: Path) -> str | None:
        for pattern in self.file_ignore_patterns:
            if fnmatch.fnmatch(path.name, pattern):
                return "IGNORED_BY_FILE_GLOB_RULE"

        try:
            size = path.stat().st_size
            if size == 0:
                return "EMPTY_FILE"
            if self.max_size_bytes and size > self.max_size_bytes:
                return "LARGE_FILE"
        except OSError:
            return "ERROR_READING_SIZE"

        return None

    def _clean_content(self, content: str) -> tuple[str, int]:
        content = self.blob_pattern.sub("NULL /* BLOB REMOVED */", content)

        lines = content.splitlines()
        width = len(str(len(lines)))

        numbered = "\n".join(
            f"{str(i + 1).rjust(width)} | {line}"
            for i, line in enumerate(lines)
        )

        return numbered, len(lines)


    # -------------------------------------------------
    # Worker
    # -------------------------------------------------

    async def _process_single_file(
        self,
        src_path: Path,
        result_queue: asyncio.Queue,
    ) -> None:
        async with self.semaphore:
            try:
                rel_path = src_path.relative_to(self.source_dir)
                dest_path = self.output_root / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                async with aiofiles.open(src_path, "r", encoding="utf-8") as f:
                    content = await f.read()

                processed_content, total_loc = self._clean_content(content)

                async with aiofiles.open(dest_path, "w", encoding="utf-8") as f:
                    await f.write(processed_content)

                await result_queue.put(
                    ProcessedFileDTO(
                        file_id=uuid4().hex,
                        file_name=src_path.name,
                        file_path=str(Path(self.output_subdir) / rel_path),
                        total_loc=total_loc,
                    )
                )

            except UnicodeDecodeError:
                await result_queue.put(
                    UnProcessedFileDTO(
                        file_name=src_path.name,
                        file_path=str(src_path),
                        ignore_reason="BINARY_CONTENT_DETECTED",
                    )
                )
            except Exception as e:
                await result_queue.put(
                    UnProcessedFileDTO(
                        file_name=src_path.name,
                        file_path=str(src_path),
                        ignore_reason=f"ERROR: {e}",
                    )
                )


    # -------------------------------------------------
    # Collector
    # -------------------------------------------------

    async def _collect_results(
        self,
        queue: asyncio.Queue,
        expected_items: int,
    ) -> tuple[list[ProcessedFileDTO], list[UnProcessedFileDTO]]:
        processed: list[ProcessedFileDTO] = []
        ignored: list[UnProcessedFileDTO] = []

        for _ in range(expected_items):
            item = await queue.get()

            if isinstance(item, ProcessedFileDTO):
                processed.append(item)
            else:
                ignored.append(item)

            queue.task_done()

        return processed, ignored

    # -------------------------------------------------
    # Public API
    # -------------------------------------------------

    async def process_async(
        self,
        clean_first: bool = False,
    ) -> tuple[list[ProcessedFileDTO], list[UnProcessedFileDTO]]:

        self.logger.info(f"Starting async processing from: {self.source_dir}")

        if clean_first:
            await asyncio.to_thread(self._cleanup_target)

        result_queue: asyncio.Queue = asyncio.Queue()
        tasks: list[asyncio.Task] = []
        expected_results = 0

        for root, dirs, files in os.walk(self.source_dir):
            root_path = Path(root)
            for dirname in dirs[:]:
                dir_path = root_path / dirname
                
                if self._should_ignore_dir(dir_path):
                    # MAGIC FIX: Removing it from 'dirs' prevents os.walk from entering it
                    dirs.remove(dirname) 

                    self.logger.debug(f"Ignoring directory: {dir_path}")
                    await result_queue.put(
                        UnProcessedFileDTO(
                            file_name=dirname,
                            file_path=str(dir_path),
                            ignore_reason="IGNORED_BY_DIRECTORY_GLOB_RULE",
                        )
                    )
                    expected_results += 1

            for filename in files:
                file_path = root_path / filename

                # Check file ignore rules
                ignore_reason = self._should_ignore_file(file_path)
                if ignore_reason:
                    await result_queue.put(
                        UnProcessedFileDTO(
                            file_name=filename,
                            file_path=str(file_path),
                            ignore_reason=ignore_reason,
                        )
                    )
                    expected_results += 1
                    continue

                # Process valid file
                expected_results += 1
                tasks.append(
                    asyncio.create_task(
                        self._process_single_file(file_path, result_queue)
                    )
                )

        collector_task = asyncio.create_task(
            self._collect_results(result_queue, expected_results)
        )

        await asyncio.gather(*tasks)
        processed, ignored = await collector_task
        self.logger.info(f"Processing complete. Processed: {len(processed)}, Ignored: {len(ignored)}")
        return processed, ignored

    # -------------------------------------------------
    # Cleanup
    # -------------------------------------------------

    def _cleanup_target(self) -> None:
        if self.source_dir == self.target_dir:
            self.logger.error(
                "SAFETY WARNING: Target directory equals source directory. Cleanup aborted."
            )
            return

        if self.output_root.exists():
            shutil.rmtree(self.output_root)
            self.logger.info(f"Target directory cleaned: {self.output_root}")
        else:
            self.logger.info(f"Target directory does not exist, no cleanup needed: {self.output_root}")