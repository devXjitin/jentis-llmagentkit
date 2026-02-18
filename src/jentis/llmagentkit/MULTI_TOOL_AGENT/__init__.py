"""
Multi Tool Agent Module

Provides an AI agent that executes multiple tools in parallel for fast results.
Part of the Jentis LLM Agent Kit.

Example:
    >>> from jentis.llmagentkit import Create_MultiTool_Agent
    >>> from jentis.core import tool
    >>>
    >>> agent = Create_MultiTool_Agent(llm=my_llm, verbose=True, max_workers=5)
    >>> agent.add_tools(tool1, tool2)
    >>> result = agent.invoke("Gather data from multiple sources")
"""

from .base import Create_MultiTool_Agent
from jentis.core import Tool, tool

__all__ = ["Create_MultiTool_Agent", "Tool", "tool"]

__version__ = "1.0.0"
