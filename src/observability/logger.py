"""
Structured logging system for agent observability.
Provides consistent logging across all agents and components.

FEATURE COVERED: Observability - Logging
"""

import structlog
import logging
import sys
from pathlib import Path
from datetime import datetime
from src.utils.config import Config

def setup_logger(name: str = "productivity_agent") -> structlog.BoundLogger:
    """
    Setup structured logger with consistent formatting.
    
    Args:
        name: Logger name (typically module or agent name)
    
    Returns:
        Configured structlog logger
    
    Usage:
        logger = setup_logger("collector_agent")
        logger.info("task_collected", task_id="123", task_name="Write code")
    """
    
    # Create logs directory
    log_dir = Config.PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Log file with timestamp
    log_file = log_dir / f"agent_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, Config.LOG_LEVEL),
    )
    
    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(file_handler)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    return structlog.get_logger(name)


class AgentLogger:
    """
    Enhanced logger specifically for agent operations.
    Provides methods for common agent logging patterns.
    """
    
    def __init__(self, agent_name: str):
        self.logger = setup_logger(agent_name)
        self.agent_name = agent_name
    
    def log_agent_start(self, task_info: dict):
        """Log when an agent starts processing"""
        self.logger.info(
            "agent_started",
            agent=self.agent_name,
            task_info=task_info
        )
    
    def log_agent_complete(self, result: dict, duration_ms: float):
        """Log when an agent completes processing"""
        self.logger.info(
            "agent_completed",
            agent=self.agent_name,
            result_summary=result,
            duration_ms=duration_ms
        )
    
    def log_tool_use(self, tool_name: str, tool_input: dict):
        """Log when an agent uses a tool"""
        self.logger.info(
            "tool_used",
            agent=self.agent_name,
            tool=tool_name,
            input=tool_input
        )
    
    def log_error(self, error: Exception, context: dict):
        """Log errors with full context"""
        self.logger.error(
            "agent_error",
            agent=self.agent_name,
            error_type=type(error).__name__,
            error_message=str(error),
            context=context,
            exc_info=True
        )
    
    def log_decision(self, decision: str, reasoning: dict):
        """Log agent decisions and reasoning"""
        self.logger.info(
            "agent_decision",
            agent=self.agent_name,
            decision=decision,
            reasoning=reasoning
        )