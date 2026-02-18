"""
Tool Executor Utility

Executes tool functions with dynamic parameter handling.

Author: Jentis Developer
Version: 1.0.0
"""

import json
from typing import Any, Dict, Union


def Tool_Executor(
    tool_name: str,
    tool_parameters: Union[Dict[str, Any], str, None],
    available_tools: Dict[str, Dict[str, Any]]
) -> Any:
    """
    Execute a tool function with the provided parameters.
    
    Args:
        tool_name: Name of the tool to execute
        tool_parameters: Parameters as dictionary, JSON string, or None
                        Example: {"param1": "value1", "param2": "value2"}
        available_tools: Dictionary mapping tool names to tool definitions
                        Each tool must have a "function" key
        
    Returns:
        Result from tool execution or error message string
        
    Examples:
        >>> Tool_Executor("calculator", {"expression": "25 * 4"}, tools)
        100
        
        >>> Tool_Executor("get_time", None, tools)
        "2026-01-18 10:30:00"
        
        >>> Tool_Executor("greet", '{"name": "Alice"}', tools)
        "Hello, Alice!"
    """
    # Validate tool exists
    if tool_name not in available_tools:
        return f"Error: Tool '{tool_name}' not found in available tools"
    
    tool_definition = available_tools[tool_name]
    
    # Validate tool definition structure
    if "function" not in tool_definition:
        return f"Error: Tool '{tool_name}' has invalid definition (missing 'function' key)"
    
    tool_function = tool_definition["function"]
    
    # Validate tool_function is callable
    if not callable(tool_function):
        return f"Error: Tool '{tool_name}' function is not callable"
    
    # Normalize parameters
    params = _normalize_parameters(tool_parameters)
    
    if isinstance(params, str) and params.startswith("Error:"):
        return params  # Return error from normalization
    
    # Execute tool function
    try:
        if params and isinstance(params, dict):
            return tool_function(**params)
        else:
            return tool_function()
    except TypeError as e:
        return f"Error: Invalid parameters for tool '{tool_name}' - {str(e)}"
    except Exception as e:
        return f"Error executing tool '{tool_name}': {type(e).__name__}: {str(e)}"


def _normalize_parameters(
    tool_parameters: Union[Dict[str, Any], str, None]
) -> Union[Dict[str, Any], str]:
    """
    Normalize tool parameters to a dictionary format.
    
    Args:
        tool_parameters: Raw parameters in various formats
        
    Returns:
        Dictionary of parameters or error message string
    """
    # Handle None/empty cases
    if tool_parameters is None or tool_parameters == "None" or tool_parameters == "":
        return {}
    
    # Handle string parameters (JSON)
    if isinstance(tool_parameters, str):
        try:
            parsed = json.loads(tool_parameters)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError as e:
            return f"Error: Invalid JSON format in parameters - {str(e)}"
    
    # Handle dictionary parameters
    if isinstance(tool_parameters, dict):
        return tool_parameters
    
    # Unsupported parameter type
    return f"Error: Unsupported parameter type '{type(tool_parameters).__name__}'. Expected dict, JSON string, or None"