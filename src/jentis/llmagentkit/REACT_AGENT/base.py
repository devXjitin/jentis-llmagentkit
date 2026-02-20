"""
ReAct Agent (Reasoning + Acting)

An advanced AI agent that combines reasoning and tool execution in an iterative loop.
This agent thinks through problems step-by-step while taking actions using tools.

Based on the ReAct (Reasoning + Acting) paradigm from "ReAct: Synergizing Reasoning and Acting in Language Models"
"""

import re
import json
from typing import Optional
from .prompt import PREFIX_PROMPT, LOGIC_PROMPT, SUFFIX_PROMPT
from ...utils.tool_executor import Tool_Executor
from ...utils.logger import AgentLogger


class Create_ReAct_Agent:
    """
    ReAct Agent that combines reasoning and tool execution.
    Uses the ReAct (Reasoning + Acting) paradigm for step-by-step problem solving.
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
        self.logger = AgentLogger(verbose=verbose, agent_name="ReAct Agent", full_output=full_output)

        if prompt is not None:
            self.logger.info("Using custom agent introduction")
            self.prompt_template = prompt + "\n\n" + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = True
        else:
            self.prompt_template = PREFIX_PROMPT + LOGIC_PROMPT + SUFFIX_PROMPT
            self.custom_prompt = False
    
    # ------------------ INTERNAL HELPERS ------------------

    def _parser(self, response):
        """Parse LLM response to extract thought, action, action input, and final answer."""
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

        thought = parsed_json.get("Thought")
        action = parsed_json.get("Action")
        action_input = parsed_json.get("Action Input")
        final_answer = parsed_json.get("Final Answer")

        # Normalize to None
        if thought in ("None", "null", ""):
            thought = None
        if action in ("None", "null", ""):
            action = None
        if action_input in ("None", "null", ""):
            action_input = None
        if final_answer in ("None", "null", ""):
            final_answer = None

        return thought, action, action_input, final_answer
    
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
            + (f"\nParameters: " + ", ".join(
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
        scratchpad = ""
        iteration = 0
        max_iterations = 15
        
        while iteration < max_iterations:
            iteration += 1
            self.logger.iteration(iteration)
            
            # Get LLM response
            full_prompt = f"{prompt}\n{scratchpad}" if scratchpad else prompt
            response = self.llm.generate_response(full_prompt)
            
            try:
                thought, action, action_input, final_answer = self._parser(response)
            except Exception as e:
                error_msg = f"Error parsing LLM response: {str(e)}"
                self._log(error_msg, "error")
                
                # Add guidance to scratchpad and retry
                scratchpad += f"\n\n--- Error at Step {iteration} ---"
                scratchpad += f"\nYour response was not in valid JSON format."
                scratchpad += f"\nYou MUST respond with JSON in this exact format:"
                scratchpad += f"\n```json"
                scratchpad += f'\n{{"Thought": "your reasoning", "Action": "tool_name", "Action Input": {{"param": "value"}}, "Final Answer": null}}'
                scratchpad += f"\n```"
                scratchpad += f"\nError: {str(e)[:150]}"
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
            
            # CASE 2 — Tool needs to be called
            if action:
                self.logger.action(action, action_input)
                observation = Tool_Executor(action, action_input, self.tools)
                self.logger.observation(observation)

                # Update scratchpad with ReAct cycle
                scratchpad += f"\n\n--- Step {iteration} ---"
                if thought:
                    scratchpad += f"\nThought: {thought}"
                scratchpad += f"\nAction: {action}"
                scratchpad += f"\nAction Input: {action_input}"
                scratchpad += f"\nObservation: {observation}"
                
            else:
                # No action and no final answer - continue thinking
                if thought:
                    scratchpad += f"\n\n--- Thought {iteration} ---"
                    scratchpad += f"\n{thought}"

        error_msg = "Error: Maximum reasoning iterations reached."
        self._log(error_msg, "error")
        return error_msg
