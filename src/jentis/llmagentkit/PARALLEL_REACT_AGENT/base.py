"""
Parallel ReAct Agent

An intelligent agent that combines the transparency of ReAct (Reasoning + Acting)
with the speed of parallel tool execution. Provides visible reasoning while
executing multiple independent tools simultaneously.
"""

import re
import json
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompt import PREFIX_PROMPT, LOGIC_PROMPT, SUFFIX_PROMPT
from ...utils.tool_executor import Tool_Executor
from ...utils.logger import AgentLogger


class Create_ParallelReAct_Agent:
    """
    Parallel ReAct Agent - Combines reasoning with parallel tool execution.
    
    Features:
    - Explicit reasoning (transparent thought process)
    - Parallel tool execution (fast performance)
    - Intelligent batching (knows when to parallelize)
    - Multi-stage workflows (can do sequential when needed)
    """

    def __init__(
        self, 
        llm,
        verbose: bool = False,
        full_output: bool = False,
        prompt: Optional[str] = None,
        memory=None,
        max_workers: int = 5,
    ) -> None:
        self.tools = {}
        self.llm = llm
        self.verbose = verbose
        self.full_output = full_output
        self.memory = memory
        self.max_workers = max_workers
        self.logger = AgentLogger(verbose=verbose, agent_name="ParallelReAct Agent", full_output=full_output)

        if prompt is not None:
            self.logger.info("Using custom agent introduction")
            self.prompt_template = prompt + "\n\n" + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = True
        else:
            self.prompt_template = PREFIX_PROMPT + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = False

    # ------------------ INTERNAL HELPERS ------------------

    def _parser(self, response):
        """Parse LLM response to extract thought, tool calls, and final answer."""
        # Try to find JSON block with code fence
        json_match = re.search(r"```json\s*(\{.*)\s*```", response, re.DOTALL)
        if not json_match:
            json_match = re.search(r"'''json\s*(\{.*)\s*'''", response, re.DOTALL)
        
        # If still no match, try without code fence
        if not json_match:
            json_match = re.search(r"(\{[\s\S]*\})", response)

        if not json_match:
            raise ValueError(f"Invalid response format: No JSON block found.\nResponse: {response[:200]}")

        json_str = json_match.group(1).strip()
        
        # Find the matching closing brace for the JSON object
        brace_count = 0
        json_end = -1
        for i, char in enumerate(json_str):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if json_end > 0:
            json_str = json_str[:json_end]
        
        # Fix double braces that LLM might copy from prompt template
        json_str = json_str.replace('{{', '{').replace('}}', '}')
        
        try:
            parsed_json = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in response: {e}\nResponse snippet: {response[:200]}")

        thought = parsed_json.get("thought")
        tool_calls = parsed_json.get("tool_calls", [])
        final_answer = parsed_json.get("final_answer")

        # Normalize
        if thought in ("None", "null", ""):
            thought = None
        if final_answer in ("None", "null", ""):
            final_answer = None
        
        # Ensure tool_calls is a list
        if not isinstance(tool_calls, list):
            tool_calls = []

        return thought, tool_calls, final_answer

    def _execute_tool(self, tool_name, tool_params):
        """Execute a single tool and return result."""
        try:
            result = Tool_Executor(tool_name, tool_params, self.tools)
            return {
                "tool": tool_name,
                "status": "success",
                "result": result
            }
        except Exception as e:
            return {
                "tool": tool_name,
                "status": "error",
                "result": f"Error: {str(e)}"
            }

    def _execute_tools_parallel(self, tool_calls):
        """Execute multiple tools in parallel."""
        if not tool_calls:
            return []

        results = []
        
        # Log parallel execution start
        tool_names = [tc.get("tool") for tc in tool_calls]
        self.logger.parallel_start(len(tool_calls), tool_names)

        # Execute in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_tool = {
                executor.submit(
                    self._execute_tool, 
                    tc.get("tool"), 
                    tc.get("params", {})
                ): tc.get("tool") 
                for tc in tool_calls
            }
            
            for future in as_completed(future_to_tool):
                tool_name = future_to_tool[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Log individual result
                    success = result["status"] == "success"
                    result_str = str(result["result"])[:150]
                    self.logger.parallel_result(tool_name, success, result_str)
                    
                except Exception as e:
                    error_result = {
                        "tool": tool_name,
                        "status": "error",
                        "result": f"Exception during execution: {str(e)}"
                    }
                    results.append(error_result)
                    self.logger.parallel_result(tool_name, False, str(e))

        return results

    def _log(self, message, level="info"):
        if self.verbose:
            getattr(self.logger, level if hasattr(self.logger, level) else "info")(message)

    # ------------------ TOOL MANAGEMENT ------------------

    def add_tool(self, name, description, function, parameters=None):
        self.tools[name] = {
            "description": description,
            "function": function,
            "parameters": parameters or {}
        }

    def add_tools(self, *tools):
        from jentis.core import tool as tool_decorator
        added_count = 0

        for item in tools:
            if hasattr(item, "__iter__") and not isinstance(item, (str, bytes)):
                try:
                    for sub_tool in list(item):
                        if hasattr(sub_tool, "to_dict"):
                            self.tools[sub_tool.name] = sub_tool.to_dict()
                            added_count += 1
                    continue
                except Exception:
                    pass

            if callable(item):
                if hasattr(item, "to_dict"):
                    self.tools[item.name] = item.to_dict()
                    added_count += 1
                else:
                    tool_obj = tool_decorator(item)
                    if hasattr(tool_obj, "to_dict"):
                        self.tools[tool_obj.name] = tool_obj.to_dict()
                        added_count += 1

        return added_count

    # ------------------ CORE EXECUTION ------------------

    def invoke(self, query):
        if not self.llm:
            raise ValueError("LLM not provided.")
        if not self.tools:
            raise ValueError("No tools added. Call add_tool() or add_tools() before invoking.")

        if self.memory:
            self.memory.add_user_message(query)
            self._log("Added user message to memory", "info")

        # Build tool list string
        tool_list_str = "\n".join(
            f"    - {name}: {info['description']}"
            + (f"\n      Parameters: " + ", ".join(
                f"{p} ({v.get('type', 'str')}, {'required' if v.get('required', True) else 'optional'})"
                for p, v in info.get('parameters', {}).items()
              ) if info.get('parameters') else "")
            for name, info in self.tools.items()
        )

        # Build memory context
        memory_context = ""
        if self.memory and (context := self.memory.get_context()):
            memory_context = f"\n\nConversation History:\n{context}"

        # Build tool list and compile base prompt
        compiled_prompt = self.prompt_template.replace("{tool_list}", tool_list_str).replace(
            "{previous_context}", memory_context
        )
        
        # Escape any curly braces from tool descriptions to prevent format() errors
        compiled_prompt = compiled_prompt.replace("{", "{{").replace("}", "}}")
        compiled_prompt = compiled_prompt.replace("{{user_input}}", "{user_input}")

        self.logger.agent_start(query)

        prompt = compiled_prompt.format(user_input=query)
        all_tool_results = []  # Accumulate ALL tool results across iterations
        iteration = 0
        max_iterations = 10

        while iteration < max_iterations:
            iteration += 1
            self.logger.iteration(iteration)

            # Build cumulative context from ALL previous tool results
            tool_results_context = ""
            if all_tool_results:
                tool_results_context = "\n\n=== COMPLETED TOOL RESULTS (Use this data, do NOT repeat these calls) ===\n"
                for idx, result in enumerate(all_tool_results, 1):
                    tool_results_context += f"\n[{idx}] Tool: {result['tool']}\n"
                    tool_results_context += f"    Status: {result['status']}\n"
                    tool_results_context += f"    Result: {result['result']}\n"
                tool_results_context += "\n=== END OF COMPLETED RESULTS ===\n"
                tool_results_context += "\nIMPORTANT: You already have the above data. Provide final_answer if you have all needed info, or call ONLY NEW tools for missing data.\n"

            # Add tool results context from previous iteration
            full_prompt = prompt + tool_results_context

            response = self.llm.generate_response(full_prompt)
            try:
                thought, tool_calls, final_answer = self._parser(response)
            except Exception as e:
                error_msg = f"Error parsing LLM response: {str(e)}"
                self._log(error_msg, "error")
                
                # Add guidance and retry
                tool_results_context += f"\n\n--- Error at Step {iteration} ---"
                tool_results_context += f"\nYour response was not in valid JSON format."
                tool_results_context += f"\nYou MUST respond with JSON in this exact format:"
                tool_results_context += f"\n```json"
                tool_results_context += f'\n{{"thought": "your reasoning", "tool_calls": [{{"tool": "name", "params": {{}}}}, ...], "final_answer": null}}'
                tool_results_context += f"\n```"
                tool_results_context += f"\nError: {str(e)[:150]}"
                continue

            # Display thought if present
            if thought:
                self.logger.thought(thought)

            # CASE 1 — Final answer ready (no more tool use)
            if final_answer:
                if isinstance(final_answer, str):
                    final_answer = final_answer.encode("utf-8").decode("unicode_escape")

                if self.memory:
                    self.memory.add_ai_message(final_answer)
                    self.logger.memory_action("Added AI response to memory")

                self.logger.agent_end(final_answer)
                return final_answer

            # CASE 2 — Tools need to be called
            if tool_calls:
                # Execute all tools in parallel
                results = self._execute_tools_parallel(tool_calls)

                # Accumulate results to the global list
                all_tool_results.extend(results)
                
            else:
                # No tools and no final answer - shouldn't happen but continue
                if thought:
                    # Just thinking, continue
                    pass
                else:
                    self._log("No tool calls, no final answer, and no thought", "error")

        error_msg = "Error: Maximum reasoning iterations reached."
        self._log(error_msg, "error")
        return error_msg
