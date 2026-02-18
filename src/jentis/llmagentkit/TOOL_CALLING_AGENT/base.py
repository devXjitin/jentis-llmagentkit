import re
import json
from typing import Optional
from .prompt import PREFIX_PROMPT, LOGIC_PROMPT, SUFFIX_PROMPT
from ...utils.tool_executor import Tool_Executor
from ...utils.logger import AgentLogger


class Create_ToolCalling_Agent:
    """
    Optimized Tool Calling Agent — compatible with strict JSON-based tool invocation logic.
    Uses `null` (not "None") in prompt format and responses.
    """

    def __init__(
        self, 
        llm,
        verbose: bool = False,
        full_output: bool = False,
        prompt: Optional[str] = None,
        memory=None,
    ) -> None:
        self.tools = {}
        self.llm = llm
        self.verbose = verbose
        self.full_output = full_output
        self.memory = memory
        self.logger = AgentLogger(verbose=verbose, agent_name="ToolCalling Agent", full_output=full_output)

        if prompt is not None:
            self.logger.info("Using custom agent introduction")
            self.prompt_template = prompt + "\n\n" + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = True
        else:
            self.prompt_template = PREFIX_PROMPT + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = False

    # ------------------ INTERNAL HELPERS ------------------

    def _parser(self, response):
        """Parse LLM response to extract tool call, parameters, and final response."""
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

        tool_call = parsed_json.get("Tool call")
        tool_params = parsed_json.get("Tool Parameters")
        final_response = parsed_json.get("Final Response")

        # Normalize to None
        if tool_call in ("None", "null", ""):
            tool_call = None
        if tool_params in ("None", "null", ""):
            tool_params = None
        if final_response in ("None", "null", ""):
            final_response = None

        return tool_call, tool_params, final_response

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
                    # Already a Tool object
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
        tool_history = []
        iteration = 0
        max_iterations = 10

        while iteration < max_iterations:
            iteration += 1
            self.logger.iteration(iteration)

            # Add tool history context
            context_prompt = prompt
            if tool_history:
                history_str = "\n\n".join(
                    f"Previous Tool: {t['name']}\nResult: {t['result']}"
                    for t in tool_history
                )
                context_prompt += f"\n\n--- Tool Execution History ---\n{history_str}\n---"

            response = self.llm.generate_response(context_prompt)
            try:
                tool_name, tool_params, final_response = self._parser(response)
                # Log the exact JSON response from LLM
                self.logger.llm_response(tool_name, tool_params, final_response)
            except Exception as e:
                error_msg = f"Error parsing LLM response: {str(e)}"
                self._log(error_msg, "error")
                return error_msg

            # CASE 1 — Final response ready (no more tool use)
            if not tool_name:
                final_answer = final_response or "No final response provided."
                if isinstance(final_answer, str):
                    final_answer = final_answer.encode("utf-8").decode("unicode_escape")

                if self.memory:
                    self.memory.add_ai_message(final_answer)
                    self.logger.memory_action("Added AI response to memory")

                self.logger.agent_end(final_answer)
                return final_answer

            # CASE 2 — Tool needs to be called
            tool_result = Tool_Executor(tool_name, tool_params, self.tools)
            self.logger.observation(tool_result)

            # Store tool execution in history
            tool_history.append({"name": tool_name, "result": tool_result})

        error_msg = "Error: Maximum reasoning iterations reached."
        self._log(error_msg, "error")
        return error_msg
