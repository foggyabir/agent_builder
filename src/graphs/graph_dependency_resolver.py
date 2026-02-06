import asyncio
from pathlib import Path
from langgraph.graph.state import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langchain.messages import SystemMessage, HumanMessage, ToolMessage, AnyMessage

from typing_extensions import Literal, TypedDict, Annotated
import operator

from llms import LLMRegistry, GPTLLM
from tools import FileNameSearchTool, ReadFileTool
from utils import PromptRegistry
from .models.file_dependency import FileDependency

class ResolverState(TypedDict):
    target_file: str
    dependencies: FileDependency | None
    messages: Annotated[list[AnyMessage], operator.add]

class GraphDependencyResolver:
    def __init__(self, source: str, prompt_registry: PromptRegistry) -> None:
        self.source = source
        self.prompt_registry = prompt_registry
        self.llm = LLMRegistry().get_gpt_llm(llm_type=GPTLLM.GPT_5_NANO, reasoning_effort=None)
        self.read_file_tool = ReadFileTool(working_directory=Path(self.source))
        self.node_tools = [FileNameSearchTool(working_directory=Path(self.source))]
        self.tools_by_name= {tool.name: tool for tool in self.node_tools}
        self.file_content = None

    async def node(self, state: ResolverState):
        self.file_content = await self.read_file_tool.arun({"relative_path": f"{state['target_file']}"}) if self.file_content is None else self.file_content
        sys_prompt = SystemMessage(self.prompt_registry.get_prompt(self.prompt_registry.file_dependency_pmt))
        human_prompt = HumanMessage(f"Analyze the file content and extract dependencies:\n\n{self.file_content}")
        llm = self.llm.bind_tools(
            self.node_tools,
            response_format=FileDependency,
            strict=True
        )

        response = await llm.ainvoke([sys_prompt, human_prompt] + state["messages"])
        print(response)
        if response.tool_calls:
            return {"messages": [response]}

        return {"dependencies": response.content, "messages": [response]}
    
    async def tool_node(self, state: ResolverState):
        async def run_tool(tool_call):
            try:
                tool = self.tools_by_name[tool_call["name"]]
                observation = await tool.ainvoke(tool_call["args"])
                return ToolMessage(
                    content=observation,
                    tool_call_id=tool_call["id"]
                )
            except Exception as e:
                return ToolMessage(
                    content=f"Tool error: {str(e)}",
                    tool_call_id=tool_call["id"]
                )

        tool_calls = state["messages"][-1].tool_calls

        results = await asyncio.gather(
            *(run_tool(tc) for tc in tool_calls)
        )

        return {"messages": results}

    
    def should_continue(self, state: ResolverState) -> Literal["tool_node", END]:
        """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

        messages = state["messages"]
        last_message = messages[-1]

        if last_message.tool_calls:
            return "tool_node"

        return END
    
    def build(self) -> CompiledStateGraph:
        builder = StateGraph(ResolverState)
        builder.add_node("llm", self.node)
        builder.add_node("tool_node", self.tool_node)

        builder.add_edge(START, "llm")
        builder.add_conditional_edges("llm", self.should_continue, ["tool_node", END])
        builder.add_edge("tool_node", "llm")

        return builder.compile()
