"""
Google Search tool for agents.
Allows agents to search the web for information.

FEATURE COVERED: Built-in Tools (Google Search)
"""

from typing import Dict, List, Any
from src.observability.logger import setup_logger

logger = setup_logger("search_tool")


class GoogleSearchTool:
    """
    Wrapper for Google Search functionality.
    
    This implements the Built-in Tools (Google Search) requirement.
    
    Note: In actual implementation with ADK, this would use
    the built-in Google Search tool. This is a mock for demonstration.
    """
    
    def __init__(self):
        logger.info("google_search_tool_initialized")
    
    def search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search Google and return results.
        
        Tool Specification:
        - Tool Name: google_search
        - Input: query string, max_results
        - Output: list of search results
        
        Usage by agent:
            results = search_tool.search("Python async programming tutorial")
        """
        logger.info("google_search", query=query, max_results=max_results)
        
        # In real implementation, this would call Google Search API
        # For demo purposes, we'll return mock results
        
        mock_results = [
            {
                "title": f"Result for: {query} - Resource 1",
                "url": f"https://example.com/result1",
                "snippet": f"Comprehensive guide about {query}. Learn the fundamentals and advanced concepts...",
                "relevance_score": 0.95
            },
            {
                "title": f"Best practices for {query}",
                "url": f"https://example.com/result2",
                "snippet": f"Expert tips and tricks for {query}. Improve your skills with these proven methods...",
                "relevance_score": 0.88
            },
            {
                "title": f"{query} - Complete Tutorial",
                "url": f"https://example.com/result3",
                "snippet": f"Step-by-step tutorial covering everything you need to know about {query}...",
                "relevance_score": 0.82
            }
        ]
        
        # Limit to max_results
        results = mock_results[:max_results]
        
        logger.info("google_search_complete", query=query, results_count=len(results))
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    
    def search_for_task_resources(self, task_name: str) -> List[str]:
        """
        Search for resources related to a specific task.
        Returns a list of helpful URLs.
        
        Usage:
            resources = search_tool.search_for_task_resources("Learn Python")
        """
        results = self.search(f"how to {task_name} tutorial guide")
        
        if results["success"]:
            return [r["url"] for r in results["results"]]
        
        return []


# Global search tool instance
_search_tool = GoogleSearchTool()

def get_search_tool() -> GoogleSearchTool:
    """Get the global search tool instance"""
    return _search_tool