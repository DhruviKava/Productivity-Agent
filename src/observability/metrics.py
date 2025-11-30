"""
Metrics collection for monitoring agent performance.
Tracks counts, durations, success rates, etc.

FEATURE COVERED: Observability - Metrics
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List
import json
from pathlib import Path

from src.utils.config import Config
from src.observability.logger import setup_logger

logger = setup_logger("metrics")


class MetricsCollector:
    """
    Collects and aggregates metrics about agent performance.
    Tracks agent executions, tool usage, success rates, etc.
    """
    
    def __init__(self):
        self.metrics: Dict[str, List] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.metrics_file = Config.DATA_DIR / "metrics.json"
    
    def record_counter(self, metric_name: str, increment: int = 1):
        """
        Increment a counter metric.
        
        Usage:
            metrics.record_counter("tasks_processed", 1)
            metrics.record_counter("agent_errors", 1)
        """
        self.counters[metric_name] += increment
        logger.info(
            "metric_counter",
            metric=metric_name,
            value=self.counters[metric_name]
        )
    
    def record_duration(self, metric_name: str, duration_ms: float):
        """
        Record a duration metric.
        
        Usage:
            metrics.record_duration("agent_execution_time", 1523.5)
        """
        self.metrics[f"{metric_name}_duration_ms"].append({
            "timestamp": datetime.now().isoformat(),
            "value": duration_ms
        })
        logger.info(
            "metric_duration",
            metric=metric_name,
            duration_ms=duration_ms
        )
    
    def record_gauge(self, metric_name: str, value: float):
        """
        Record a gauge metric (point-in-time value).
        
        Usage:
            metrics.record_gauge("active_tasks", 15)
            metrics.record_gauge("completion_rate", 0.87)
        """
        self.metrics[metric_name].append({
            "timestamp": datetime.now().isoformat(),
            "value": value
        })
        logger.info(
            "metric_gauge",
            metric=metric_name,
            value=value
        )
    
    def record_agent_execution(
        self,
        agent_name: str,
        duration_ms: float,
        success: bool,
        task_count: int = 1
    ):
        """Record full agent execution metrics"""
        self.record_counter(f"{agent_name}_executions")
        self.record_duration(f"{agent_name}_duration", duration_ms)
        
        if success:
            self.record_counter(f"{agent_name}_success")
        else:
            self.record_counter(f"{agent_name}_failure")
        
        self.record_gauge(f"{agent_name}_tasks_processed", task_count)
    
    def get_summary(self) -> Dict:
        """Get summary of all collected metrics"""
        summary = {
            "counters": dict(self.counters),
            "metric_counts": {
                key: len(values) 
                for key, values in self.metrics.items()
            },
            "generated_at": datetime.now().isoformat()
        }
        
        # Calculate averages for duration metrics
        averages = {}
        for key, values in self.metrics.items():
            if "duration_ms" in key:
                avg = sum(v["value"] for v in values) / len(values)
                averages[f"{key}_avg"] = round(avg, 2)
        
        summary["averages"] = averages
        return summary
    
    def save_metrics(self):
        """Save metrics to file"""
        data = {
            "counters": dict(self.counters),
            "metrics": {
                key: list(values) 
                for key, values in self.metrics.items()
            },
            "summary": self.get_summary()
        }
        
        with open(self.metrics_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info("metrics_saved", file=str(self.metrics_file))
    
    def load_metrics(self):
        """Load previously saved metrics"""
        if self.metrics_file.exists():
            with open(self.metrics_file, 'r') as f:
                data = json.load(f)
                self.counters = defaultdict(int, data.get("counters", {}))
                self.metrics = defaultdict(
                    list,
                    {k: list(v) for k, v in data.get("metrics", {}).items()}
                )
            logger.info("metrics_loaded", file=str(self.metrics_file))


# Global metrics collector instance
_metrics_collector = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return _metrics_collector