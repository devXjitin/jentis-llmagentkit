"""
Jentis LLM Agent Kit
====================

A collection of AI agent architectures for different use cases.
All agents are part of the `jentis` namespace.

Available Agents:
    - Create_ReAct_Agent         — Reasoning + Acting (Thought → Action → Observation loop)
    - Create_MultiTool_Agent     — Parallel multi-tool execution without reasoning overhead  
    - Create_ParallelReAct_Agent — Parallel tool execution with full reasoning visibility
    - Create_ToolCalling_Agent   — Sequential tool calling without reasoning

Example:
    >>> from jentis.llmagentkit import Create_ReAct_Agent
    >>> from jentis.core import tool
    >>>
    >>> agent = Create_ReAct_Agent(llm=my_llm, verbose=True)
    >>> agent.add_tools(my_tool)
    >>> response = agent.invoke("Your query here")
"""

from .REACT_AGENT import Create_ReAct_Agent
from .MULTI_TOOL_AGENT import Create_MultiTool_Agent
from .PARALLEL_REACT_AGENT import Create_ParallelReAct_Agent
from .TOOL_CALLING_AGENT import Create_ToolCalling_Agent

__all__ = [
    "Create_ReAct_Agent",
    "Create_MultiTool_Agent",
    "Create_ParallelReAct_Agent",
    "Create_ToolCalling_Agent",
]

__version__ = "1.0.0"
