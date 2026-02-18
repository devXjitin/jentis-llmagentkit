"""
ReAct Agent Module (Reasoning + Acting)

Provides an AI agent that combines reasoning and tool execution in an iterative loop.
Part of the Jentis LLM Agent Kit.

Based on the ReAct paradigm: "ReAct: Synergizing Reasoning and Acting in Language Models"

Main Components:
- Create_ReAct_Agent: Agent class with Thought → Action → Observation loop
- Memory integration support (optional)
- Custom prompt support
- Verbose mode with colored terminal output

Example:
    >>> from jentis.llmagentkit import Create_ReAct_Agent
    >>> from jentis.core import tool
    >>>
    >>> agent = Create_ReAct_Agent(llm=my_llm, verbose=True)
    >>>
    >>> @tool
    >>> def search(query: str) -> str:
    ...     '''Search the internet for information.'''
    ...     return f"Results for {query}"
    >>>
    >>> agent.add_tools(search)
    >>> result = agent.invoke("Search for Python tutorials")
"""

from .base import Create_ReAct_Agent
from jentis.core import Tool, tool

__all__ = ["Create_ReAct_Agent", "Tool", "tool"]

__version__ = "1.0.0"
