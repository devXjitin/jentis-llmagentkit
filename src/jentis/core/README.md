# 🎯 Core System

The foundation of Jentis Agentic Kit's tool management system.

## Tool Decorator

Create tools effortlessly using the `@tool` decorator:

```python
from jentis.core import tool

@tool
def calculator(expression: str) -> str:
    """Performs mathematical calculations.
    
    Args:
        expression: Mathematical expression to evaluate
    """
    return str(eval(expression))

# Add to agent
agent.add_tools(calculator)
```

## Features

- Clean decorator syntax (`@tool`)
- Automatic parameter extraction from type hints
- Smart docstring parsing for descriptions
- Type-safe parameter validation
- Flexible tool definition
- Zero-boilerplate tool creation

## Tool Class

For more control, use the `Tool` class directly:

```python
from jentis.core import Tool

def my_function(query: str) -> str:
    return f"Result for: {query}"

tool = Tool(
    name="my_tool",
    description="Does something useful",
    function=my_function,
    parameters={
        "query": {
            "type": "string",
            "description": "The search query",
            "required": True
        }
    }
)

agent.add_tools(tool)
```

## Type Support

Automatic type conversion from Python hints:

| Python Type | Tool Schema |
|-------------|-------------|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |
| `list` | `array` |
| `dict` | `object` |
| `List[str]` | `array` (items: string) |
| `Optional[str]` | `string` (not required) |

## Docstring Parsing

Descriptions are extracted automatically:

```python
@tool
def search(query: str, max_results: int = 10) -> str:
    """Search for information.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return
        
    Returns:
        Search results as JSON string
    """
    ...
```

Extracted:
- Tool description: "Search for information."
- `query` description: "The search query string"
- `max_results` description: "Maximum number of results to return"

## Creating Multi-Function Tools

For tools with multiple functions, yield multiple Tool objects:

```python
from jentis.core import Tool
from typing import Iterator

def YouTubeSearchTool() -> Iterator[Tool]:
    def search(query: str) -> str:
        ...
    
    def get_details(video_id: str) -> str:
        ...
    
    yield Tool(
        name="youtube_search",
        description="Search YouTube videos",
        function=search,
        parameters={"query": {"type": "string", "required": True}}
    )
    
    yield Tool(
        name="youtube_details",
        description="Get video details",
        function=get_details,
        parameters={"video_id": {"type": "string", "required": True}}
    )
```

## Best Practices

1. **Clear Names**: Use descriptive, lowercase names with underscores
2. **Good Descriptions**: Write clear descriptions for LLM understanding
3. **Type Hints**: Always include type hints for automatic schema
4. **Docstrings**: Document parameters in docstrings
5. **Return JSON**: Return JSON strings for complex data
