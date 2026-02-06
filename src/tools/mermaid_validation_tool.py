import asyncio
import subprocess
import json
from typing import Type
from pydantic import BaseModel, Field
from .base import ToolBase

class _MermaidValidationInput(BaseModel):
    code: str = Field(
        description=(
            "The raw mermaid diagram code syntax to be validated. "
            "Do not include markdown backticks (```mermaid ... ```), just the code itself."
        )
    )

class MermaidValidationTool(ToolBase):
    """A tool for validating Mermaid diagrams."""
    name: str = "MermaidValidationTool"
    description: str = (
        "Use this tool to validate if a Mermaid.js diagram code is syntactically correct "
        "before returning it to the user. Returns valid=true or an error message."
    )
    args_schema: Type[BaseModel] = _MermaidValidationInput
    # --- INJECTED VARIABLES ---
    script_path: str = "validate.js"
    node_executable: str = "node"

    def _run(self, code: str) -> dict:
        """
        Validate Mermaid code using mermaid.parse via Node.js.
        """
        # Ensure we aren't passing empty strings or markdown formatting if the LLM forgot
        clean_code = code.replace("```mermaid", "").replace("```", "").strip()
        self.logger.debug(f"Validating Mermaid code {clean_code[100:]}\n")
        try:
            # Note: Ensure 'node' is in your system PATH
            proc = subprocess.run(
                [self.node_executable, self.script_path, clean_code],
                capture_output=True,
                text=True,
                encoding='utf-8', # Explicit encoding for Windows safety
                check=False       # We handle errors via stdout/stderr check
            )
            
            # If the script prints JSON to stdout, parse it
            if proc.stdout:
                try:
                    return json.loads(proc.stdout.strip())
                except json.JSONDecodeError:
                    self.logger.debug(f"[MermaidValidationTool] Validation Failed: \n{proc.stdout}\n")
                    return {"valid": False, "error": f"Output parsing failed: {proc.stdout}"}
            
            # If stdout is empty, check stderr
            if proc.stderr:
                self.logger.debug(f"[MermaidValidationTool] Validation Failed: \n{proc.stderr.strip()}\n")
                return {"valid": False, "error": proc.stderr.strip()}

            return {"valid": False, "error": "Unknown error: No output from validation script."}

        except FileNotFoundError:
            self.logger.debug(f"[MermaidValidationTool] Validation Failed: Node.js executable not found. Please install Node.js.")
            return {"valid": False, "error": "Node.js executable not found. Please install Node.js."}
        except Exception as e:
            self.logger.debug(f"[MermaidValidationTool] Validation Exception: {e}\n")
            return {"valid": False, "error": str(e)}

    async def _arun(self, code: str):
        return await asyncio.to_thread(self._run, code)

