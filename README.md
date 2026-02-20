# Jentis LLM Agent Kit

[![PyPI version](https://badge.fury.io/py/jentis-llmagentkit.svg)](https://badge.fury.io/py/jentis-llmagentkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A production-ready collection of AI agent architectures built on top of `jentis.core`.  
Each agent is optimized for different trade-offs between **speed**, **reasoning depth**, and **tool parallelism**.

---

## What's New in v1.0.1
- **Critical Fix**: Resolved JSON parsing issues across all agents for robust tool execution.
- **Prompt Optimization**: Enhanced system prompts for better adherence to JSON protocols.
- **Agent Improvements**:
  - `ToolCalling Agent`: Streamlined for direct execution.
  - `ReAct Agent`: Enforced strict Thought-Action loop.
  - `MultiTool Agent`: Fixed parallel execution logic.
  - `ParallelReAct Agent`: Optimized for concurrent reasoning tasks.

---

## Installation

```bash
pip install jentis-llmagentkit
```

---

## Quick Start

```python
from jentis.llmagentkit import Create_ReAct_Agent
from jentis.core import tool

@tool
def search(query: str) -> str:
    """Search the internet for information."""
    return f"Results for: {query}"

# Assuming you have an LLM instance
agent = Create_ReAct_Agent(llm=my_llm, verbose=True)
agent.add_tools(search)
response = agent.invoke("What is quantum computing?")
print(response)
```

---

## Available Agents

### 1. **ToolCalling Agent** — Sequential, No Reasoning

```python
from jentis.llmagentkit import Create_ToolCalling_Agent

agent = Create_ToolCalling_Agent(llm=my_llm, verbose=True)
```

- **Execution**: One tool at a time, sequentially
- **Reasoning**: None — direct tool invocation
- **Use Case**: Simple tasks needing one or a few tool calls
- **Speed**: ★★☆

---

### 2. **ReAct Agent** — Sequential + Reasoning

```python
from jentis.llmagentkit import Create_ReAct_Agent

agent = Create_ReAct_Agent(llm=my_llm, verbose=True)
```

- **Execution**: One tool at a time, sequentially
- **Reasoning**: Full Thought → Action → Observation loop
- **Use Case**: Complex problems requiring step-by-step reasoning
- **Speed**: ★☆☆ (reasoning overhead)

---

### 3. **MultiTool Agent** — Parallel, No Reasoning

```python
from jentis.llmagentkit import Create_MultiTool_Agent

agent = Create_MultiTool_Agent(llm=my_llm, verbose=True, max_workers=5)
```

- **Execution**: Multiple tools simultaneously in parallel
- **Reasoning**: None — direct parallel execution
- **Use Case**: Fast data gathering from multiple independent sources
- **Speed**: ★★★

---

### 4. **ParallelReAct Agent** — Parallel + Reasoning ⭐ *Recommended*

```python
from jentis.llmagentkit import Create_ParallelReAct_Agent

agent = Create_ParallelReAct_Agent(llm=my_llm, verbose=True, max_workers=5)
```

- **Execution**: Multiple tools in parallel, chained across iterations
- **Reasoning**: Full thought process visible at every step
- **Use Case**: Complex tasks requiring both speed and transparency
- **Speed**: ★★★

---

## Common Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm` | LLM | **required** | Language model instance |
| `verbose` | `bool` | `False` | Print colored execution logs |
| `full_output` | `bool` | `False` | Show full output without truncation |
| `prompt` | `str` | `None` | Custom system prompt prefix |
| `memory` | Memory | `None` | Conversation memory object |
| `max_workers` | `int` | `5` | Parallel thread count (MultiTool/ParallelReAct only) |

---

## Tool Registration

```python
from jentis.core import tool

# Decorator — automatic schema extraction from type hints + docstring
@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

# Register one or more tools
agent.add_tools(calculator, another_tool)

# Or register manually with explicit schema
agent.add_tool(
    name="calculator",
    description="Evaluate a mathematical expression.",
    function=lambda expression: str(eval(expression)),
    parameters={"expression": {"type": "str", "required": True}}
)
```

---

## Agent Comparison

| Feature | ToolCalling | ReAct | MultiTool | ParallelReAct |
|---------|:-----------:|:-----:|:---------:|:-------------:|
| Execution | Sequential | Sequential | Parallel | Parallel |
| Reasoning | ✗ | ✓ | ✗ | ✓ |
| Speed | ★★ | ★ | ★★★ | ★★★ |
| Complexity handling | Simple | Complex | Simple | Complex |
| Tool chaining | Manual | Automatic | Manual | Automatic |
| Transparency | Low | High | Low | High |

---

## Choosing the Right Agent

```
Single tool, simple query?
  → ToolCalling Agent

Need visible reasoning at each step?
  → ReAct Agent

Multiple independent data sources, speed matters?
  → MultiTool Agent

Complex reasoning AND multiple tools AND speed?
  → ParallelReAct Agent  ← recommended default
```

---

## Example: ParallelReAct Workflow

```
Query: "Find a Machine Learning tutorial"

Iteration 1  (parallel)
  ├─ youtube_search("Machine Learning tutorial")
  └─ wikipedia_search("Machine Learning")

Iteration 2  (sequential — depends on iteration 1 results)
  └─ youtube_transcript(video_id=<result from iteration 1>)

Iteration 3
  └─ Final Answer  (synthesizes all collected data)
```

---

## License

MIT License - see [LICENSE](LICENSE) file for details

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## Project Structure

```
src/jentis/
├── core/                    # Tool system (@tool decorator, Tool class)
├── llmagentkit/             # Agent implementations
│   ├── TOOL_CALLING_AGENT/
│   ├── REACT_AGENT/
│   ├── MULTI_TOOL_AGENT/
│   └── PARALLEL_REACT_AGENT/
└── utils/                   # AgentLogger, Tool_Executor
```
