"""
Tool System - Professional-Grade Tool Management
=================================================

A modern, independent tool system with decorators and automatic parameter 
extraction from function signatures. Designed for seamless integration with 
AI agents and multi-agent systems in the Jentis Agentic Kit.

Features:
    - Clean decorator syntax (@tool)
    - Automatic parameter extraction from type hints
    - Smart docstring parsing for descriptions
    - Type-safe parameter validation
    - Flexible tool definition (decorator or direct instantiation)
    - Zero-boilerplate tool creation
    - Framework-agnostic design
    
Architecture:
    - Tool: Core class representing a callable tool with metadata
    - @tool: Decorator for automatic tool creation from functions
    - Parameter introspection via Python's inspect module
    - Type hint support for automatic schema generation

Example:
    >>> from jentis.core import tool
    >>> 
    >>> @tool
    >>> def calculator(expression: str) -> str:
    ...     '''Performs mathematical calculations.'''
    ...     return str(eval(expression))
    >>> 
    >>> # Add to agent
    >>> agent.add_tools(calculator)
    >>> 
    >>> # Direct call
    >>> result = calculator("2 + 2")

Author: Jentis Developer
Version: 1.0.0
License: MIT
"""

import inspect
import re
from typing import Callable, Optional, Dict, Any, List, Union, get_type_hints, get_origin, get_args


# ============================================================================
# Pre-compiled Regex Patterns (for performance)
# ============================================================================

_ARGS_PATTERN = re.compile(r'(?:Args?|Arguments?|Parameters?):\s*\n((?:\s+\w+.*\n?)+)', re.IGNORECASE)
_PARAM_PATTERN = re.compile(r'\s+(\w+)\s*(?:\([^)]+\))?\s*:\s*(.+?)(?=\n\s+\w+\s*(?:\([^)]+\))?\s*:|$)', re.DOTALL)
_NUMPY_PATTERN = re.compile(r'Parameters\s*\n\s*-+\s*\n((?:.*\n?)+?)(?:\n\s*(?:Returns|Yields|Raises|See Also|Notes|Examples)|\Z)', re.IGNORECASE)
_NUMPY_PARAM_PATTERN = re.compile(r'(\w+)\s*:\s*[^\n]+\n\s+(.+?)(?=\n\w+\s*:|$)', re.DOTALL)


# ============================================================================
# Type Utilities
# ============================================================================

# Type mapping for performance (avoid repeated dictionary creation)
_TYPE_MAP = {
    str: "str",
    int: "int",
    float: "float",
    bool: "bool",
    list: "list",
    dict: "dict",
    tuple: "tuple",
    set: "set",
    bytes: "bytes",
}

def _convert_type_to_string(param_type: Any) -> str:
    """
    Convert Python type hints to string representation for tool schema.
    
    Optimized for low latency with early returns and pre-computed mappings.
    
    Args:
        param_type: Python type hint to convert
        
    Returns:
        String representation of the type (e.g., "str", "int", "list", "dict")
        
    Examples:
        >>> _convert_type_to_string(str)
        'str'
        >>> _convert_type_to_string(Optional[int])
        'int'
        >>> _convert_type_to_string(List[str])
        'list'
    """
    # Fast path for None/Any
    if param_type is None or param_type == Any:
        return "any"
    
    # Fast path for strings
    if isinstance(param_type, str):
        return param_type.lower()
    
    # Fast path for basic types
    type_str = _TYPE_MAP.get(param_type)
    if type_str:
        return type_str
    
    # Handle generic types
    origin = get_origin(param_type)
    if origin is None:
        return "str"  # Default fallback
    
    # Handle Optional/Union
    if origin is Union:
        args = get_args(param_type)
        for arg in args:
            if arg is not type(None):
                return _convert_type_to_string(arg)
        return "any"
    
    # Handle collection types
    if origin in (list, List):
        return "list"
    if origin in (dict, Dict):
        return "dict"
    if origin is tuple:
        return "tuple"
    if origin is set:
        return "set"
    
    return "str"  # Default fallback


def _extract_param_descriptions_from_docstring(func: Callable) -> Dict[str, str]:
    """
    Extract parameter descriptions from function docstring.
    
    Optimized with pre-compiled regex patterns for low latency.
    Supports Google-style, NumPy-style, and reStructuredText docstrings.
    
    Args:
        func: Function to extract parameter descriptions from
        
    Returns:
        Dictionary mapping parameter names to their descriptions
        
    Examples:
        Google-style:
            Args:
                query (str): The search query to execute
                limit (int): Maximum number of results
                
        NumPy-style:
            Parameters
            ----------
            query : str
                The search query to execute
            limit : int
                Maximum number of results
    """
    docstring = func.__doc__
    if not docstring:
        return {}
    
    # Try Google/Sphinx style with pre-compiled pattern
    args_match = _ARGS_PATTERN.search(docstring)
    
    if args_match:
        args_section = args_match.group(1)
        return {
            match.group(1): re.sub(r'\s+', ' ', match.group(2)).strip()
            for match in _PARAM_PATTERN.finditer(args_section)
        }
    
    # Try NumPy style with pre-compiled pattern
    numpy_match = _NUMPY_PATTERN.search(docstring)
    if numpy_match:
        params_section = numpy_match.group(1)
        return {
            match.group(1): re.sub(r'\s+', ' ', match.group(2)).strip()
            for match in _NUMPY_PARAM_PATTERN.finditer(params_section)
        }
    
    return {}


# ============================================================================
# Tool Decorator
# ============================================================================

def tool(
    func: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    return_direct: bool = False
) -> Union['Tool', Callable[..., 'Tool']]:
    """
    Decorator to convert a function into a Tool with automatic metadata extraction.
    
    This decorator intelligently extracts:
        - Tool name from function name
        - Description from docstring
        - Parameters with types from function signature
        - Parameter descriptions from docstring Args section
        - Required/optional status from default values
    
    Args:
        func: Function to convert to a tool (when used as @tool)
        name: Optional custom tool name (defaults to function name)
        description: Optional custom description (defaults to docstring)
        return_direct: Whether the tool returns final answer directly to user
    
    Returns:
        Tool instance with complete metadata
        
    Examples:
        Basic usage:
            >>> @tool
            >>> def calculator(expression: str) -> str:
            ...     '''Performs mathematical calculations on expressions.'''
            ...     return str(eval(expression))
        
        With custom metadata:
            >>> @tool(name="web_search", description="Search the internet")
            >>> def search(query: str, limit: int = 10) -> str:
            ...     '''Search for information.
            ...     
            ...     Args:
            ...         query: The search query to execute
            ...         limit: Maximum number of results to return
            ...     '''
            ...     return f"Found {limit} results for {query}"
        
        With complex types:
            >>> @tool
            >>> def process_data(
            ...     items: List[str],
            ...     config: Optional[Dict[str, Any]] = None
            ... ) -> Dict[str, Any]:
            ...     '''Process a list of items with optional configuration.'''
            ...     return {"processed": len(items)}
    
    Note:
        Type hints are required for proper parameter extraction.
        Without type hints, parameters default to 'str' type.
    """
    def decorator(f: Callable) -> 'Tool':
        # Extract tool metadata (optimized)
        tool_name = name or f.__name__
        
        # Get description efficiently
        if description:
            tool_description = description
        else:
            doc = f.__doc__
            if doc:
                tool_description = doc.strip().split('\n', 1)[0].strip()
            else:
                tool_description = "No description provided"
        
        # Extract parameter information (single pass)
        sig = inspect.signature(f)
        type_hints = get_type_hints(f)
        param_descriptions = _extract_param_descriptions_from_docstring(f)
        
        # Build parameters dict efficiently
        parameters = {
            param_name: {
                "type": _convert_type_to_string(type_hints.get(param_name, Any)),
                "description": param_descriptions.get(param_name, f"The {param_name} parameter"),
                "required": param.default == inspect.Parameter.empty
            }
            for param_name, param in sig.parameters.items()
            if param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        }
        
        return Tool(
            name=tool_name,
            description=tool_description,
            function=f,
            parameters=parameters,
            return_direct=return_direct
        )
    
    # Handle both @tool and @tool() or @tool(name="...", description="...")
    if func is not None:
        # Used as @tool (without parentheses)
        return decorator(func)
    else:
        # Used as @tool() or @tool(name="...")
        return decorator




# ============================================================================
# Tool Class
# ============================================================================

class Tool:
    """
    Represents a callable tool with complete metadata and schema.
    
    A Tool wraps a Python function with structured metadata that enables:
        - Automatic documentation generation
        - Parameter validation
        - Schema-based invocation by AI agents
        - Direct or indirect execution
    
    Attributes:
        name (str): Unique identifier for the tool
        description (str): Human-readable description of functionality
        function (Callable): The actual Python function to execute
        parameters (Dict): Schema defining input parameters with types and descriptions
        return_direct (bool): Whether tool output goes directly to user
    
    Examples:
        Direct instantiation:
            >>> def multiply(a: int, b: int) -> int:
            ...     return a * b
            >>> 
            >>> tool = Tool(
            ...     name="multiply",
            ...     description="Multiply two numbers",
            ...     function=multiply,
            ...     parameters={
            ...         "a": {"type": "int", "description": "First number", "required": True},
            ...         "b": {"type": "int", "description": "Second number", "required": True}
            ...     }
            ... )
        
        Via decorator (recommended):
            >>> @tool
            >>> def multiply(a: int, b: int) -> int:
            ...     '''Multiply two numbers together.'''
            ...     return a * b
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        return_direct: bool = False
    ):
        """
        Initialize a Tool instance.
        
        Args:
            name: Unique tool name (used as identifier by agents)
            description: Clear description of what the tool does
            function: The callable Python function to execute
            parameters: Parameter schema dict mapping param names to their metadata.
                Each parameter should have: type, description, required
            return_direct: If True, tool output is returned directly to user.
                If False, output goes back to the agent for further processing
        
        Raises:
            ValueError: If name is empty or function is not callable
        """
        if not name or not isinstance(name, str):
            raise ValueError("Tool name must be a non-empty string")
        
        if not callable(function):
            raise ValueError("Tool function must be callable")
        
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters or {}
        self.return_direct = return_direct
    
    def run(self, *args, **kwargs) -> Any:
        """
        Execute the tool's function with provided arguments.
        
        Args:
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        
        Returns:
            Result of the function execution
        
        Raises:
            Any exception raised by the underlying function
        
        Example:
            >>> tool = Tool("add", "Add numbers", lambda a, b: a + b)
            >>> result = tool.run(5, 3)
            >>> print(result)  # 8
        """
        return self.function(*args, **kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tool to dictionary representation.
        
        Useful for serialization, logging, or passing to external systems.
        Note: The function itself is included but may not be serializable.
        
        Returns:
            Dictionary containing tool metadata
        
        Example:
            >>> tool_dict = tool.to_dict()
            >>> print(tool_dict.keys())
            dict_keys(['name', 'description', 'function', 'parameters', 'return_direct'])
        """
        return {
            "name": self.name,
            "description": self.description,
            "function": self.function,
            "parameters": self.parameters,
            "return_direct": self.return_direct
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the tool's schema without the function reference.
        
        Useful for generating API documentation or passing schema to LLMs.
        
        Returns:
            Dictionary with tool metadata excluding the function object
        
        Example:
            >>> schema = tool.get_schema()
            >>> # Safe to JSON serialize or send to LLM
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "return_direct": self.return_direct
        }
    
    def validate_parameters(self, **kwargs) -> List[str]:
        """
        Validate provided parameters against the tool's schema.
        
        Optimized for performance with minimal allocations.
        
        Args:
            **kwargs: Parameters to validate
        
        Returns:
            List of error messages (empty if valid)
        
        Example:
            >>> errors = tool.validate_parameters(query="test", limit=10)
            >>> if errors:
            ...     print("Validation errors:", errors)
        """
        errors = []
        provided = kwargs.keys()
        
        # Check required parameters in single pass
        for param_name, param_info in self.parameters.items():
            if param_info.get("required", False) and param_name not in provided:
                errors.append(f"Missing required parameter: {param_name}")
        
        # Check for unexpected parameters
        unexpected = provided - self.parameters.keys()
        if unexpected:
            errors.append(f"Unexpected parameters: {', '.join(unexpected)}")
        
        return errors
    
    def __call__(self, *args, **kwargs) -> Any:
        """
        Allow tool to be called directly like a function.
        
        Example:
            >>> result = tool(arg1="value", arg2=123)
        """
        return self.run(*args, **kwargs)
    
    def __repr__(self) -> str:
        """String representation of the tool."""
        params = list(self.parameters.keys())
        return f"Tool(name='{self.name}', parameters={params})"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        param_count = len(self.parameters)
        return f"Tool '{self.name}': {self.description} ({param_count} parameters)"


# ============================================================================
# Exports
# ============================================================================

__all__ = ["Tool", "tool"]
