"""
Tool Calling Agent Module

Provides an AI agent that calls tools sequentially without explicit reasoning overhead.
Part of the Jentis LLM Agent Kit.

Main Components:
- Create_ToolCalling_Agent: Agent class with tool registration and sequential execution
- Memory integration support (optional)
- Custom prompt support
- Verbose mode with colored terminal output

Example:
    >>> from jentis.llmagentkit import Create_ToolCalling_Agent
    >>> from jentis.core import tool
    >>>
    >>> agent = Create_ToolCalling_Agent(llm=my_llm, verbose=True)
    >>>
    >>> @tool
    >>> def calculator(expression: str) -> str:
    ...     '''Evaluate a math expression.'''
    ...     return str(eval(expression))
    >>>
    >>> agent.add_tools(calculator)
    >>> result = agent.invoke("What is 25 * 4?")
"""

from .base import Create_ToolCalling_Agent
from jentis.core import Tool, tool

__all__ = ["Create_ToolCalling_Agent", "Tool", "tool"]

__version__ = "1.0.1"
