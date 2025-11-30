"""
Distributed tracing for agent workflows.
Tracks the flow of requests through multiple agents.

FEATURE COVERED: Observability - Tracing
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter
)
from opentelemetry.sdk.resources import Resource
from contextlib import contextmanager
from typing import Dict, Any
import time

from src.utils.config import Config

# Initialize tracer provider
resource = Resource(attributes={
    "service.name": "productivity-agent-system"
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

# Add console exporter for development
if Config.ENABLE_TRACING:
    console_exporter = ConsoleSpanExporter()
    span_processor = BatchSpanProcessor(console_exporter)
    tracer_provider.add_span_processor(span_processor)

# Get tracer instance
tracer = trace.get_tracer(__name__)


class AgentTracer:
    """
    Wrapper for OpenTelemetry tracing with agent-specific patterns.
    Tracks agent execution flow and performance.
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.tracer = tracer
    
    @contextmanager
    def trace_operation(self, operation_name: str, attributes: Dict[str, Any] = None):
        """
        Context manager for tracing agent operations.
        
        Usage:
            with tracer.trace_operation("prioritize_tasks", {"task_count": 5}):
                # ... agent code ...
                pass
        """
        span_name = f"{self.agent_name}.{operation_name}"
        
        with self.tracer.start_as_current_span(span_name) as span:
            # Add standard attributes
            span.set_attribute("agent.name", self.agent_name)
            span.set_attribute("operation.name", operation_name)
            
            # Add custom attributes
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(f"custom.{key}", str(value))
            
            # Record start time
            start_time = time.time()
            
            try:
                yield span
            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
            finally:
                # Record duration
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("duration_ms", duration_ms)
    
    def create_span(self, operation_name: str):
        """Create a new span for manual management"""
        span_name = f"{self.agent_name}.{operation_name}"
        return self.tracer.start_span(span_name)


def trace_agent_communication(from_agent: str, to_agent: str, message_type: str):
    """
    Trace communication between agents (A2A protocol).
    Creates a span that links agent interactions.
    """
    with tracer.start_as_current_span("agent_communication") as span:
        span.set_attribute("from_agent", from_agent)
        span.set_attribute("to_agent", to_agent)
        span.set_attribute("message_type", message_type)
        return span