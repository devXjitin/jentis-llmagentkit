"""
Multi Tool Call Agent

A fast, efficient agent that executes multiple tools in parallel without reasoning overhead.
Perfect for quick information gathering and simple queries requiring multiple data sources.
"""

import re
import json
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompt import PREFIX_PROMPT, LOGIC_PROMPT, SUFFIX_PROMPT
from ...utils.tool_executor import Tool_Executor
from ...utils.logger import AgentLogger


class Create_MultiTool_Agent:
    """
    Multi Tool Call Agent - Executes multiple tools in parallel for fast results.
    No reasoning overhead, just direct tool execution and response.
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
        self.logger = AgentLogger(verbose=verbose, agent_name="MultiTool Agent", full_output=full_output)

        if prompt is not None:
            self.logger.info("Using custom agent introduction")
            self.prompt_template = prompt + "\n\n" + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = True
        else:
            self.prompt_template = PREFIX_PROMPT + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = False

    # ------------------ INTERNAL HELPERS ------------------

    def _parser(self, response):
        """Parse LLM response to extract tool calls and final response."""
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
        
        try:
            parsed_json = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format in response: {e}\nResponse snippet: {response[:200]}")

        tool_calls = parsed_json.get("tool_calls", [])
        final_response = parsed_json.get("final_response")

        # Normalize
        if final_response in ("None", "null", ""):
            final_response = None
        
        # Ensure tool_calls is a list
        if not isinstance(tool_calls, list):
            tool_calls = []

        return tool_calls, final_response

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

        # Escape braces in dynamic content to prevent format() errors
        tool_list_str = tool_list_str.replace("{", "{{").replace("}", "}}")
        memory_context = memory_context.replace("{", "{{").replace("}", "}}")

        # Build tool list and compile base prompt
        compiled_prompt = self.prompt_template.replace("{tool_list}", tool_list_str).replace(
            "{previous_context}", memory_context
        )
        
        self.logger.agent_start(query)

        prompt = compiled_prompt.format(user_input=query)
        tool_results_context = ""
        iteration = 0
        max_iterations = 5  # Should rarely need more than 2-3

        while iteration < max_iterations:
            iteration += 1
            self.logger.iteration(iteration)

            # Add tool results context from previous iteration
            full_prompt = prompt + tool_results_context

            response = self.llm.generate_response(full_prompt)
            try:
                tool_calls, final_response = self._parser(response)
            except Exception as e:
                error_msg = f"Error parsing LLM response: {str(e)}"
                self._log(error_msg, "error")
                return error_msg

            # CASE 1 — Final response ready (no more tool use)
            if final_response:
                if isinstance(final_response, str):
                    final_response = final_response.encode("utf-8").decode("unicode_escape")

                if self.memory:
                    self.memory.add_ai_message(final_response)
                    self.logger.memory_action("Added AI response to memory")

                self.logger.agent_end(final_response)
                return final_response

            # CASE 2 — Tools need to be called
            if tool_calls:
                # Execute all tools in parallel
                results = self._execute_tools_parallel(tool_calls)

                # Build context for next iteration with helpful hints
                tool_results_context = "\n\n--- Tool Execution Results ---\n"
                has_errors = False
                for result in results:
                    tool_results_context += f"\nTool: {result['tool']}\n"
                    tool_results_context += f"Status: {result['status']}\n"
                    tool_results_context += f"Result: {result['result']}\n"
                    
                    # Check for common errors and provide hints
                    if result['status'] == 'error' or 'No output' in str(result['result']) or result['result'] == '':
                        has_errors = True
                
                if has_errors:
                    tool_results_context += "\nNote: Some tools returned empty or error results. Consider trying alternative approaches.\n"
                tool_results_context += "--- End Results ---\n"
            else:
                # No tools and no final response - shouldn't happen
                self._log("No tool calls and no final response", "error")
                return "Error: Agent did not provide tools or final response"

        error_msg = "Error: Maximum iterations reached."
        self._log(error_msg, "error")
        return error_msg
