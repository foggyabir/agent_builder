from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

import logging

from graphs import DependencyResolverWrapper, FileDependency
from utils import PromptRegistry

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout), # Output logs to standard output (console)
        #logging.FileHandler('app.log')     # Output logs to a file
    ]
)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

target = r'D:\.Agent_Workspace'
pr = PromptRegistry().register_all_prompts()
resolver = DependencyResolverWrapper(source=target, prompt_registry=pr)
# graph = resolver.build()

async def main():
    result = await resolver.ainvoke(["legacy_source/src/app/app.module.ts", "legacy_source/src/app/app-routing.module.ts"])
    for dep in result:
        print("\n\n***********************\n\n")
        if dep:
            print(dep.model_dump_json(indent=2))
    

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())