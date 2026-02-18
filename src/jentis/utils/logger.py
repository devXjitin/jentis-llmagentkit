"""
Agent Logger Utility

Provides colored console logging for AI agents with verbose and full output modes.

Author: Jentis Developer
Version: 1.0.0
"""

import sys
from typing import Optional, Any
from datetime import datetime


class Colors:
    """ANSI color codes for terminal output."""
    
    # Basic colors
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright foreground colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"
    
    @classmethod
    def strip_colors(cls, text: str) -> str:
        """Remove all ANSI color codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)


class AgentLogger:
    """
    Colorful logger for AI agents with support for verbose mode.
    
    Features:
    - Colored console output with ANSI codes
    - Verbose mode for detailed logging
    - Timestamped messages
    - Structured logging for agent operations
    
    Example:
        >>> logger = AgentLogger(verbose=True, agent_name="MyAgent")
        >>> logger.agent_start("What is 2+2?")
        >>> logger.info("Processing query...")
        >>> logger.agent_end("The answer is 4")
    """
    
    def __init__(
        self,
        verbose: bool = False,
        agent_name: str = "Agent",
        use_colors: bool = True,
        show_timestamp: bool = False,
        full_output: bool = False,
    ) -> None:
        """
        Initialize the agent logger.
        
        Args:
            verbose: Enable verbose logging output
            agent_name: Name of the agent for log messages
            use_colors: Enable colored output (disable for log files)
            show_timestamp: Show timestamp in log messages
            full_output: Show full output without truncation
        """
        self.verbose = verbose
        self.agent_name = agent_name
        self.use_colors = use_colors and self._supports_color()
        self.show_timestamp = show_timestamp
        self.full_output = full_output
        self._iteration_count = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.start_time = None
        self.end_time = None
        self.tool_call_count = 0
    
    @staticmethod
    def _supports_color() -> bool:
        """Check if the terminal supports color output."""
        # Check if running in a TTY
        if not hasattr(sys.stdout, 'isatty') or not sys.stdout.isatty():
            # Check for common CI/CD environments that support colors
            import os
            if os.getenv('TERM') in ('xterm', 'xterm-color', 'xterm-256color', 'screen', 'screen-256color'):
                return True
            if os.getenv('COLORTERM'):
                return True
            return False
        return True
    
    def _format_message(self, message: str, color: str = "", prefix: str = "") -> str:
        """Format a log message with optional color and prefix."""
        timestamp = ""
        if self.show_timestamp:
            timestamp = f"[{datetime.now().strftime('%H:%M:%S')}] "
        
        if self.use_colors and color:
            return f"{color}{timestamp}{prefix}{message}{Colors.RESET}"
        return f"{timestamp}{prefix}{message}"
    
    def _print(self, message: str) -> None:
        """Print message to stdout."""
        print(message, flush=True)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text (rough approximation: ~4 chars per token)."""
        if not text:
            return 0
        # Rough estimation: 1 token ≈ 4 characters for English text
        # More accurate for mixed content (code, punctuation, etc.)
        return max(1, len(text) // 4)
    
    def _truncate(self, text: str, max_length: int = 500) -> str:
        """Return text without truncation."""
        return text
    
    # ==================== Core Logging Methods ====================
    
    def info(self, message: str) -> None:
        """Log an informational message."""
        if self.verbose:
            formatted = self._format_message(message, Colors.BLUE, "[INFO] ")
            self._print(formatted)
    
    def success(self, message: str) -> None:
        """Log a success message."""
        if self.verbose:
            formatted = self._format_message(message, Colors.BRIGHT_GREEN, "[SUCCESS] ")
            self._print(formatted)
    
    def warning(self, message: str) -> None:
        """Log a warning message."""
        if self.verbose:
            formatted = self._format_message(message, Colors.BRIGHT_YELLOW, "[WARNING] ")
            self._print(formatted)
    
    def error(self, message: str) -> None:
        """Log an error message."""
        if self.verbose:
            formatted = self._format_message(message, Colors.BRIGHT_RED, "[ERROR] ")
            self._print(formatted)
    
    def debug(self, message: str) -> None:
        """Log a debug message."""
        if self.verbose:
            formatted = self._format_message(message, Colors.DIM + Colors.WHITE, "[DEBUG] ")
            self._print(formatted)
    
    # ==================== Agent-Specific Methods ====================
    
    def agent_start(self, query: str) -> None:
        """Log the start of agent execution."""
        if self.verbose:
            import time
            self.start_time = time.time()
            self._print("")
            self._print(self._format_message(
                "=" * 60,
                Colors.BRIGHT_BLUE + Colors.BOLD
            ))
            self._print(self._format_message(
                f"  {self.agent_name} Started",
                Colors.BRIGHT_BLUE + Colors.BOLD
            ))
            self._print(self._format_message(
                f"  Query: {query}",
                Colors.WHITE
            ))
            self._print(self._format_message(
                "=" * 60,
                Colors.BRIGHT_BLUE
            ))
            self._iteration_count = 0
    
    def agent_end(self, response: str) -> None:
        """Log the end of agent execution."""
        if self.verbose:
            import time
            self.end_time = time.time()
            self._print("")
            self._print(self._format_message(
                "=" * 60,
                Colors.BRIGHT_GREEN + Colors.BOLD
            ))
            self._print(self._format_message(
                f"  {self.agent_name} Completed",
                Colors.BRIGHT_GREEN + Colors.BOLD
            ))
            self._print(self._format_message(
                "=" * 60,
                Colors.BRIGHT_GREEN
            ))
    
    def iteration(self, iteration_num: int) -> None:
        """Log an iteration number."""
        if self.verbose:
            self._iteration_count = iteration_num
            self._print("")
            self._print(self._format_message(
                f">>> Iteration {iteration_num}",
                Colors.BRIGHT_BLUE + Colors.BOLD
            ))
    
    def llm_response(
        self, 
        tool_name: Optional[str], 
        tool_params: Optional[Any], 
        final_response: Optional[str]
    ) -> None:
        """Log the LLM's parsed response."""
        if self.verbose:
            if tool_name:
                self._print(self._format_message(
                    f"  Tool: {tool_name}",
                    Colors.MAGENTA + Colors.BOLD
                ))
                params_str = str(tool_params) if tool_params else "None"
                self._print(self._format_message(
                    f"     Parameters: {params_str}",
                    Colors.BRIGHT_MAGENTA
                ))
            else:
                self._print(self._format_message(
                    "  Final Response Ready",
                    Colors.BRIGHT_GREEN + Colors.BOLD
                ))
            
            if final_response:
                self._print(self._format_message(
                    f"     {final_response}",
                    Colors.WHITE
                ))
    
    def observation(self, result: Any) -> None:
        """Log a tool execution result."""
        if self.verbose:
            result_str = str(result)
            self._print(self._format_message(
                f"  Result:",
                Colors.YELLOW + Colors.BOLD
            ))
            self._print(self._format_message(
                f"     {result_str}",
                Colors.BRIGHT_YELLOW
            ))
    
    def memory_action(self, message: str) -> None:
        """Log a memory-related action."""
        if self.verbose:
            self._print(self._format_message(
                f"[MEMORY] {message}",
                Colors.BLUE
            ))
    
    def tool_execution(self, tool_name: str, params: Optional[Any] = None) -> None:
        """Log the execution of a tool."""
        if self.verbose:
            self.tool_call_count += 1
            params_str = str(params) if params else "No parameters"
            self._print(self._format_message(
                f"  Executing: {tool_name}",
                Colors.YELLOW + Colors.BOLD
            ))
            self._print(self._format_message(
                f"     Parameters: {params_str}",
                Colors.BRIGHT_YELLOW
            ))
    
    def thought(self, message: str) -> None:
        """Log agent thought/reasoning (ReAct-style)."""
        if self.verbose:
            self._print(self._format_message(
                f"  [Thought] {message}",
                Colors.BRIGHT_MAGENTA + Colors.BOLD
            ))

    def action(self, tool_name: str, action_input: Optional[Any] = None) -> None:
        """Log a ReAct-style action (tool call with input)."""
        if self.verbose:
            self._print(self._format_message(
                f"  [Action] {tool_name}",
                Colors.YELLOW + Colors.BOLD
            ))
            if action_input is not None:
                self._print(self._format_message(
                    f"     Input: {action_input}",
                    Colors.BRIGHT_YELLOW
                ))

    def parallel_start(self, count: int, tool_names: list) -> None:
        """Log the start of parallel tool execution."""
        if self.verbose:
            names_str = ", ".join(str(n) for n in tool_names)
            self._print(self._format_message(
                f"  [Parallel] Executing {count} tool(s) in parallel: {names_str}",
                Colors.BRIGHT_CYAN + Colors.BOLD
            ))

    def parallel_result(self, tool_name: str, success: bool, result_preview: str) -> None:
        """Log the result of a single parallel tool execution."""
        if self.verbose:
            status_color = Colors.BRIGHT_GREEN if success else Colors.BRIGHT_RED
            status_label = "OK" if success else "FAIL"
            self._print(self._format_message(
                f"  [{status_label}] {tool_name}: {result_preview}",
                status_color
            ))

    def thinking(self, message: str) -> None:
        """Log agent thinking/reasoning process."""
        if self.verbose:
            self._print(self._format_message(
                f"  {message}",
                Colors.BRIGHT_MAGENTA
            ))
    
    def token_usage(self, input_tokens: int = 0, output_tokens: int = 0) -> None:
        """
        Track token usage for LLM calls.
        
        Args:
            input_tokens: Number of input tokens (prompt)
            output_tokens: Number of output tokens (response)
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
    
    def display_total_tokens(self, iterations: int = 0, model: str = "Unknown") -> None:
        """Display total token usage summary."""
        if self.verbose:
            total = self.total_input_tokens + self.total_output_tokens
            self._print("")
            self._print(self._format_message(
                "=" * 60,
                Colors.BRIGHT_MAGENTA
            ))
            self._print(self._format_message(
                f"Input Token: {self.total_input_tokens:,}",
                Colors.BRIGHT_CYAN
            ))
            self._print(self._format_message(
                f"Output Token: {self.total_output_tokens:,}",
                Colors.BRIGHT_YELLOW
            ))
            self._print(self._format_message(
                f"Total Token: {total:,}",
                Colors.BRIGHT_GREEN + Colors.BOLD
            ))
            
            # Display time taken if both start and end times are available
            if self.start_time is not None and self.end_time is not None:
                elapsed_time = self.end_time - self.start_time
                self._print(self._format_message(
                    f"Time Taken: {elapsed_time:.2f} seconds",
                    Colors.BRIGHT_BLUE
                ))
            
            # Display iterations and tool usage
            if iterations > 0:
                self._print(self._format_message(
                    f"Total Iterations: {iterations}",
                    Colors.BRIGHT_MAGENTA
                ))
            
            self._print(self._format_message(
                f"Total Tool Used: {self.tool_call_count}",
                Colors.BRIGHT_WHITE
            ))
            
            self._print(self._format_message(
                "=" * 60,
                Colors.BRIGHT_MAGENTA
            ))
    
    # ==================== Utility Methods ====================
    
    def section(self, title: str) -> None:
        """Log a section header."""
        if self.verbose:
            self._print(self._format_message(
                f"\n{'═' * 60}",
                Colors.BRIGHT_CYAN
            ))
            self._print(self._format_message(
                f"  {title}",
                Colors.BRIGHT_CYAN + Colors.BOLD
            ))
            self._print(self._format_message(
                f"{'═' * 60}\n",
                Colors.BRIGHT_CYAN
            ))
    
    def divider(self) -> None:
        """Print a divider line."""
        if self.verbose:
            self._print(self._format_message(
                "─" * 60,
                Colors.BRIGHT_BLACK
            ))
    
    def blank_line(self) -> None:
        """Print a blank line."""
        if self.verbose:
            self._print("")
    
    def custom(self, message: str, color: str = "", emoji: str = "") -> None:
        """Log a custom message with optional color and emoji."""
        if self.verbose:
            prefix = f"{emoji} " if emoji else ""
            formatted = self._format_message(message, color, prefix)
            self._print(formatted)
    
    def progress(self, current: int, total: int, message: str = "") -> None:
        """Log progress information."""
        if self.verbose:
            percentage = (current / total * 100) if total > 0 else 0
            bar_length = 30
            filled = int(bar_length * current / total) if total > 0 else 0
            bar = "█" * filled + "░" * (bar_length - filled)
            
            progress_msg = f"[{bar}] {percentage:.1f}% ({current}/{total})"
            if message:
                progress_msg += f" - {message}"
            
            self._print(self._format_message(
                progress_msg,
                Colors.BRIGHT_CYAN
            ))


# Convenience function for quick logger creation
def create_logger(
    verbose: bool = True,
    agent_name: str = "Agent",
    **kwargs: Any
) -> AgentLogger:
    """
    Create an AgentLogger instance with default settings.
    
    Args:
        verbose: Enable verbose logging
        agent_name: Name of the agent
        **kwargs: Additional arguments for AgentLogger
        
    Returns:
        Configured AgentLogger instance
    """
    return AgentLogger(verbose=verbose, agent_name=agent_name, **kwargs)
