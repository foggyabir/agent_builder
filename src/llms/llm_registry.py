from enum import Enum
from typing import Union

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel 

class GPTLLM(Enum):
    GPT_5_MINI = 1
    GPT_5_NANO = 2

class GPTReasoningEffort(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LLMRegistry:
    def __init__(self, openai_api_key: str = ""):
        self.openai_api_key = openai_api_key

    def get_gpt_llm(self, llm_type: GPTLLM, reasoning_effort: Union[GPTReasoningEffort , None] = None) -> BaseChatModel:
        model_name = "gpt-5-mini"
        if llm_type == GPTLLM.GPT_5_MINI:
            model_name = "gpt-5-mini"
        elif llm_type == GPTLLM.GPT_5_NANO:
            model_name = "gpt-5-nano"
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")
        reasoning: Union[dict, None] = None
        if reasoning_effort:
            reasoning = {
                "effort": reasoning_effort.value.lower(),  # 'low', 'medium', or 'high'
                "summary": "auto",  # 'detailed', 'auto', or None
            }
        return ChatOpenAI(
            model=model_name,
            temperature=0.1,
            reasoning=reasoning if reasoning else None,
        )