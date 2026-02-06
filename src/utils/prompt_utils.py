
import os
from pathlib import Path
from typing import Union
from .base import UtilBase


class _PromptUtils(UtilBase):
    # Use this class to retrieve prompt strings from various markdown files.

    def __init__(self, base_location: Union[str, None] = None):
        self.prompt_files = []
        super().__init__()
        if base_location is None:
            # search current working directory for prompts folder
            cwd = os.getcwd()
            self.logger.debug(f"Current working directory: {cwd}")
            if os.path.exists(os.path.join(cwd, "prompts")):
                base_location = os.path.join(cwd, "prompts")
            else:
                self.logger.warning("Warning: 'prompts' folder not found in current working directory. Please provide a valid base_location.")
        self._base_location:str = base_location if base_location else ""

    def register_prompt_file(self, prompt_name: str) -> '_PromptUtils':
        """Register a prompt file with a specific name."""
        self.prompt_files.append(prompt_name)
        return self

    def get_prompt(self, prompt_name: str) -> str:
        """Retrieve the content of a registered prompt file."""
        prompt_name = prompt_name if prompt_name.endswith(".md") else f"{prompt_name}.md"
        file_loc = Path(self._base_location) / prompt_name
        
        with open(file_loc, "r", encoding="utf-8") as f:
            return f.read()
        
class PromptRegistry:
    def __init__(self, prompt_loc=None):
        self.p_util = _PromptUtils(prompt_loc)

    file_dependency_pmt = "re/pmt_dep_resolver.md"

    def register_all_prompts(self)-> 'PromptRegistry':
        self.p_util.register_prompt_file(self.file_dependency_pmt) 
        return self

    def get_prompt(self, name:str)->str:
        return self.p_util.get_prompt(name)
        