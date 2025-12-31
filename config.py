"""
Configuration Module
Central configuration for the quiz bot and memory system
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent
DATABASE_DIR = BASE_DIR / "database"
BACKUP_DIR = BASE_DIR / "backups"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATABASE_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Database configuration
DATABASE_PATH = str(DATABASE_DIR / "quiz_bot.db")
SCHEMA_PATH = str(DATABASE_DIR / "schema.sql")

# Cache configuration (TTL in seconds)
CACHE_CONFIG = {
    'session_ttl': 1800,      # 30 minutes
    'user_ttl': 3600,          # 1 hour
    'leaderboard_ttl': 300,    # 5 minutes
    'quiz_ttl': 1800,          # 30 minutes
    'stats_ttl': 600,          # 10 minutes
}

# Backup configuration
BACKUP_CONFIG = {
    'auto_backup': True,
    'backup_interval_hours': 24,
    'keep_backups_days': 7,
    'backup_on_shutdown': True,
}

# Logging configuration
LOGGING_CONFIG = {
    'level': os.getenv('LOG_LEVEL', 'INFO'),
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': str(LOGS_DIR / 'quiz_bot.log'),
    'max_bytes': 10485760,  # 10MB
    'backup_count': 5,
}

# Bot configuration
BOT_CONFIG = {
    'quiz_bot_token': os.getenv('QUIZ_BOT_TOKEN', '7518438812:AAF29rspjnbm48FQMZXJBCTOL1U5HOUJC-4'),
    'auction_bot_token': os.getenv('AUCTION_BOT_TOKEN', '7392955526:AAGavuQbNQlpKV3CsPZAJzApZVIpMoqh-Fk'),
}

# Memory configuration
MEMORY_CONFIG = {
    'max_conversation_history': 10,
    'session_timeout_minutes': 60,
    'auto_save_interval_seconds': 30,
}

# Achievement thresholds
ACHIEVEMENTS = {
    'first_quiz': {
        'name': 'First Steps',
        'description': 'Completed your first quiz',
        'threshold': 1
    },
    'quiz_master': {
        'name': 'Quiz Master',
        'description': 'Completed 10 quizzes',
        'threshold': 10
    },
    'perfectionist': {
        'name': 'Perfectionist',
        'description': 'Got 100% on a quiz',
        'threshold': 100  # percentage
    },
    'dedicated': {
        'name': 'Dedicated',
        'description': 'Completed 50 quizzes',
        'threshold': 50
    },
    'legend': {
        'name': 'Legend',
        'description': 'Completed 100 quizzes',
        'threshold': 100
    },
}

# Export settings
EXPORT_CONFIG = {
    'format': 'json',
    'include_timestamps': True,
    'pretty_print': True,
}

# Feature flags
FEATURES = {
    'enable_memory': True,
    'enable_caching': True,
    'enable_backups': True,
    'enable_achievements': True,
    'enable_leaderboard': True,
    'enable_analytics': True,
}
