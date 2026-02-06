from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

import logging

from utils import FilePreprocessor

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout), # Output logs to standard output (console)
        #logging.FileHandler('app.log')     # Output logs to a file
    ]
)

source = r"D:\_projectsToBeTested\angular-weather-app-main"
target = r'D:\.Agent_Workspace'

processor = FilePreprocessor(
    source_dir=source,
    target_dir=target,
    max_size_kb=100,
    file_ignore_patterns=[".*"],
    dir_ignore_patterns=["e2e"],
    use_gitignore=True,
    max_concurrency=8,
)

async def main():
    processd, skipped = await processor.process_async(clean_first=True)
    print(f"Processed {len(processd)} files.")
    for s in skipped:
        print(f"Skipped: {s.file_path} - Reason: {s.ignore_reason}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

