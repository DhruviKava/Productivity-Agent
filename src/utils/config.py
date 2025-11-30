"""
Configuration management for the productivity agent system.
Loads settings from environment variables and provides defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Central configuration class for all settings"""
    
    # API Configuration
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
    
    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    OUTPUTS_DIR = DATA_DIR / "outputs"
    REPORTS_DIR = OUTPUTS_DIR / "reports"
    
    # Memory configuration
    MEMORY_BANK_PATH = os.getenv(
        "MEMORY_BANK_PATH", 
        str(DATA_DIR / "memory_bank.json")
    )
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))
    
    # Observability
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    
    # Agent configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not found. Please set it in .env file"
            )
        
        # Create necessary directories
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.OUTPUTS_DIR.mkdir(exist_ok=True)
        cls.REPORTS_DIR.mkdir(exist_ok=True)
        
        return True

# Validate configuration on import
Config.validate()