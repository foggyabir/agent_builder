from pathlib import Path
import sys

from pydantic import BaseModel, Field


sys.path.append(str(Path(__file__).parent.parent))
from llms import LLMRegistry, GPTLLM, GPTReasoningEffort

class OutputSchema(BaseModel):
    """Schema for response."""

    steps: list[str] = Field(..., description="List of steps for reverse engineering document generation.")

llm = LLMRegistry().get_gpt_llm(llm_type=GPTLLM.GPT_5_MINI, reasoning_effort=GPTReasoningEffort.MEDIUM)
structured_llm = llm.with_structured_output(OutputSchema)

response = structured_llm.invoke("How will you analyze a legacy angular 2+ codebase to generate a coprehensive reverse engineering document? " \
"Output a comprehensive list of steps you will take along.")

response_normal = llm.invoke("How will you analyze a legacy angular 2+ codebase to generate a coprehensive reverse engineering document? " \
"Output a comprehensive list of steps you will take along.")

print(response_normal)

for block in response_normal.content_blocks:
    if block["type"] == "reasoning":
        print(block["reasoning"])

