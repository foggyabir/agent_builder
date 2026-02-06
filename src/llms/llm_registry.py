from enum import Enum
from typing import Union

from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel 

class GPTLLM(Enum):
    GPT_5_MINI = "gpt-5-mini"
    GPT_5_NANO = "gpt-5-nano"
    GPT_41_NANO = "gpt-4.1-nano"

class GPTReasoningEffort(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LLMRegistry:
    def __init__(self, openai_api_key: str = ""):
        self.openai_api_key = openai_api_key

    def get_gpt_llm(self, llm_type: GPTLLM, reasoning_effort: Union[GPTReasoningEffort , None] = None, temperature = 0.2) -> BaseChatModel:
        model_name = llm_type.value
        
        reasoning: Union[dict, None] = None
        if reasoning_effort:
            reasoning = {
                "effort": reasoning_effort.value.lower(),  # 'low', 'medium', or 'high'
                "summary": "auto",  # 'detailed', 'auto', or None
            }
        if reasoning_effort:
            return ChatOpenAI(
                model=model_name,
                temperature=temperature,
                reasoning=reasoning,
            )
        
        return ChatOpenAI(
                model=model_name,
                temperature=temperature
            )