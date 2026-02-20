"""
Parallel ReAct Agent Module

Provides an AI agent that combines reasoning with parallel tool execution.
Part of the Jentis LLM Agent Kit.

Example:
    >>> from jentis.llmagentkit import Create_ParallelReAct_Agent
    >>> from jentis.core import tool
    >>>
    >>> agent = Create_ParallelReAct_Agent(llm=my_llm, verbose=True, max_workers=5)
    >>> agent.add_tools(tool1, tool2)
    >>> result = agent.invoke("Complex task requiring reasoning and speed")
"""

from .base import Create_ParallelReAct_Agent
from jentis.core import Tool, tool

__all__ = ["Create_ParallelReAct_Agent", "Tool", "tool"]

__version__ = "1.0.1"
