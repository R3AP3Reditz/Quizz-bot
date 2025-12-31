# Memory System Documentation

Comprehensive documentation for the Quiz Bot memory system architecture and API.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Database Layer](#database-layer)
4. [Memory Manager](#memory-manager)
5. [Caching Layer](#caching-layer)
6. [Backup System](#backup-system)
7. [API Reference](#api-reference)
8. [Usage Examples](#usage-examples)
9. [Performance Tuning](#performance-tuning)
10. [Troubleshooting](#troubleshooting)

## Overview

The memory system provides persistent storage, caching, and data management for the Quiz Bot. It consists of four main layers:

1. **Database Layer**: SQLite-based persistent storage
2. **Memory Manager**: High-level interface for data operations
3. **Caching Layer**: In-memory cache for performance
4. **Backup System**: Automatic backups and data export

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────┐
│              Quiz Bot Application                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           Memory Manager Interface               │
│  ┌──────────────┬──────────────┬──────────────┐ │
│  │SessionMemory │  UserMemory  │Conversation  │ │
│  │              │              │Memory        │ │
│  └──────────────┴──────────────┴──────────────┘ │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼────────┐ ┌─────▼──────────┐
│  Cache Layer   │ │Database Manager│
│  - Session     │ │  - CRUD Ops    │
│  - User        │ │  - Queries     │
│  - Leaderboard │ │  - Migrations  │
│  - Stats       │ │  - Indexes     │
└───────┬────────┘ └─────┬──────────┘
        │                 │
        │          ┌──────▼──────┐
        │          │SQLite DB    │
        │          │quiz_bot.db  │
        │          └─────────────┘
        │
┌───────▼────────┐
│ Backup Manager │
│  - Auto Backup │
│  - Export      │
│  - Restore     │
└────────────────┘
```

## Database Layer

### Schema Overview

The database consists of 8 main tables:

#### 1. Users Table
Stores user profiles and aggregate statistics.

```sql
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    telegram_id TEXT UNIQUE,
    username TEXT,
    first_name TEXT,
    join_date TIMESTAMP,
    total_score INTEGER DEFAULT 0,
    quizzes_taken INTEGER DEFAULT 0,
    last_active TIMESTAMP
);
```

**Key Fields:**
- `user_id`: Unique user identifier
- `total_score`: Cumulative score across all quizzes
- `quizzes_taken`: Total number of completed quizzes
- `last_active`: Last interaction timestamp

#### 2. Quiz Sessions Table
Tracks individual quiz attempts.

```sql
CREATE TABLE quiz_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    quiz_name TEXT,
    quiz_type TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    score INTEGER,
    total_questions INTEGER,
    correct_answers INTEGER,
    status TEXT DEFAULT 'in_progress'
);
```

**Status Values:**
- `in_progress`: Quiz is ongoing
- `paused`: Quiz is temporarily paused
- `completed`: Quiz finished normally
- `abandoned`: Quiz not completed

#### 3. Quiz Answers Table
Stores individual question answers.

```sql
CREATE TABLE quiz_answers (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    question_id INTEGER,
    question_text TEXT,
    user_answer TEXT,
    correct_answer TEXT,
    is_correct BOOLEAN,
    time_taken REAL,
    answered_at TIMESTAMP
);
```

#### 4. User Preferences Table
Stores user settings and preferences.

```sql
CREATE TABLE user_preferences (
    user_id INTEGER PRIMARY KEY,
    difficulty_preference TEXT DEFAULT 'medium',
    category_preference TEXT,
    notification_enabled BOOLEAN DEFAULT 1,
    auto_difficulty BOOLEAN DEFAULT 1,
    theme TEXT DEFAULT 'default'
);
```

#### 5. Conversation History Table
Tracks recent user interactions.

```sql
CREATE TABLE conversation_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message_type TEXT,
    message_text TEXT,
    context TEXT,
    timestamp TIMESTAMP
);
```

**Retention**: Automatically keeps only the last 20 interactions per user.

#### 6. User Achievements Table
Tracks earned achievements and badges.

```sql
CREATE TABLE user_achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    achievement_type TEXT,
    achievement_name TEXT,
    description TEXT,
    earned_at TIMESTAMP
);
```

#### 7. Quiz Metadata Table
Stores information about created quizzes.

```sql
CREATE TABLE quiz_metadata (
    quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_name TEXT UNIQUE,
    creator_id INTEGER,
    created_at TIMESTAMP,
    total_questions INTEGER,
    time_gap INTEGER,
    status TEXT DEFAULT 'active',
    times_played INTEGER DEFAULT 0,
    average_score REAL DEFAULT 0
);
```

#### 8. Leaderboard Cache Table
Cached leaderboard data for performance.

```sql
CREATE TABLE leaderboard_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    leaderboard_type TEXT,
    category TEXT,
    data TEXT,
    last_updated TIMESTAMP
);
```

### Indexes

Performance-optimized indexes:

```sql
CREATE INDEX idx_user_sessions ON quiz_sessions(user_id);
CREATE INDEX idx_session_answers ON quiz_answers(session_id);
CREATE INDEX idx_conversation_user ON conversation_history(user_id);
CREATE INDEX idx_leaderboard_type ON leaderboard_cache(leaderboard_type);
CREATE INDEX idx_quiz_creator ON quiz_metadata(creator_id);
CREATE INDEX idx_user_achievements ON user_achievements(user_id);
CREATE INDEX idx_session_status ON quiz_sessions(status);
CREATE INDEX idx_user_last_active ON users(last_active);
```

## Memory Manager

The Memory Manager provides a high-level interface for all data operations.

### Initialization

```python
from memory.memory_manager import MemoryManager

memory_manager = MemoryManager(db_path="database/quiz_bot.db")
```

### SessionMemory

Manages active quiz sessions.

#### Creating a Session

```python
session_id = await memory_manager.create_session(
    user_id=12345,
    quiz_name="Python Basics",
    quiz_type="multiple"
)
```

#### Adding Answers

```python
await memory_manager.add_answer(
    user_id=12345,
    question_id=1,
    question_text="What is 2+2?",
    user_answer="4",
    correct_answer="4",
    is_correct=True
)
```

#### Completing a Session

```python
results = await memory_manager.complete_session(user_id=12345)
# Returns: {'session_id': 1, 'score': 85, 'correct_answers': 17, ...}
```

### UserMemory

Manages user profiles and statistics.

#### Loading a User

```python
user = await memory_manager.load_user(
    user_id=12345,
    username="johndoe",
    first_name="John",
    telegram_id="12345"
)
```

#### Getting User Statistics

```python
stats = await memory_manager.get_user_stats(user_id=12345)
# Returns: {
#     'user_id': 12345,
#     'username': 'johndoe',
#     'total_score': 850,
#     'quizzes_taken': 10,
#     'average_score': 85,
#     'best_score': 95,
#     ...
# }
```

#### Managing Preferences

```python
# Get preferences
prefs = await memory_manager.get_user_preferences(user_id=12345)

# Update preferences
await memory_manager.update_user_preferences(
    user_id=12345,
    difficulty_preference='hard',
    notification_enabled=True
)
```

### ConversationMemory

Manages conversation history and context.

#### Adding Conversation

```python
await memory_manager.add_conversation(
    user_id=12345,
    message_type='command',
    message_text='/start',
    context='User initiated session'
)
```

#### Getting Context

```python
history = await memory_manager.get_conversation_context(
    user_id=12345,
    limit=5
)
```

## Caching Layer

The caching layer provides high-performance in-memory caching with automatic TTL and LRU eviction.

### Cache Architecture

```python
from memory.cache import get_cache

cache = get_cache()
```

### Cache Types

1. **Session Cache**: Active quiz sessions (30 min TTL)
2. **User Cache**: User profiles (1 hour TTL)
3. **Leaderboard Cache**: Rankings (5 min TTL)
4. **Quiz Cache**: Quiz data (30 min TTL)
5. **Stats Cache**: User statistics (10 min TTL)

### Usage Examples

#### Session Cache

```python
# Set session
cache.set_session(user_id=12345, session_data={'quiz': 'test'})

# Get session
session = cache.get_session(user_id=12345)

# Delete session
cache.delete_session(user_id=12345)
```

#### User Cache

```python
# Set user
cache.set_user(user_id=12345, user_data={'name': 'John'})

# Get user
user = cache.get_user(user_id=12345)

# Delete user
cache.delete_user(user_id=12345)
```

#### Leaderboard Cache

```python
# Set leaderboard
cache.set_leaderboard(leaderboard_data=[...], category='global')

# Get leaderboard
leaders = cache.get_leaderboard(category='global')

# Invalidate all leaderboards
cache.invalidate_leaderboards()
```

### Cache Statistics

```python
stats = cache.get_all_stats()
# Returns: {
#     'session_cache': {'size': 45, 'hits': 120, 'misses': 30, 'hit_rate': 80.0},
#     'user_cache': {'size': 230, 'hits': 450, 'misses': 50, 'hit_rate': 90.0},
#     ...
# }
```

### Cache Cleanup

Automatic cleanup runs every 5 minutes. Manual cleanup:

```python
cache.cleanup_all_expired()
```

## Backup System

Provides automatic backups, restore capability, and user data export.

### Initialization

```python
from utils.backup import get_backup_manager, AutoBackupScheduler

backup_manager = get_backup_manager(db_path="database/quiz_bot.db")
```

### Creating Backups

```python
# Create backup with auto-generated name
backup_path = backup_manager.create_backup()

# Create backup with custom name
backup_path = backup_manager.create_backup("my_backup.db")
```

### Listing Backups

```python
backups = backup_manager.list_backups()
# Returns: [
#     {'filename': 'backup_20250101_120000.db', 'created_at': '...', 'size_mb': 2.5},
#     ...
# ]
```

### Restoring Backups

```python
success = backup_manager.restore_backup("backup_20250101_120000.db")
```

### Automatic Backup Scheduler

```python
scheduler = AutoBackupScheduler(backup_manager, interval_hours=24)
await scheduler.start()

# Stop scheduler
scheduler.stop()
```

### Exporting User Data

GDPR-compliant user data export:

```python
export_path = backup_manager.export_user_data(user_id=12345)
# Creates: user_data_12345_timestamp.json
```

### Database Statistics

```python
stats = backup_manager.get_database_stats()
# Returns: {
#     'users_count': 150,
#     'quiz_sessions_count': 500,
#     'database_size_mb': 5.2,
#     'top_users': [...]
# }
```

## API Reference

### MemoryManager Class

#### Session Operations

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `create_session` | user_id, quiz_name, quiz_type | session_id | Create new quiz session |
| `add_answer` | user_id, question_id, question_text, user_answer, correct_answer, is_correct | None | Add answer to session |
| `complete_session` | user_id | Dict | Complete and calculate results |
| `get_active_session` | user_id | Dict | Get active session data |

#### User Operations

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `load_user` | user_id, username, first_name, telegram_id | Dict | Load or create user |
| `get_user_stats` | user_id | Dict | Get user statistics |
| `get_user_history` | user_id, limit | List[Dict] | Get quiz history |
| `update_user_preferences` | user_id, **preferences | None | Update preferences |
| `get_user_preferences` | user_id | Dict | Get preferences |

#### Leaderboard Operations

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `get_leaderboard` | limit | List[Dict] | Get global leaderboard |

#### Utility Operations

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `delete_user_data` | user_id | None | Delete all user data |
| `clear_caches` | None | None | Clear all memory caches |

## Usage Examples

### Complete Quiz Flow

```python
# Initialize
memory_manager = MemoryManager()
user_id = 12345

# Load user
await memory_manager.load_user(user_id, "john_doe", "John")

# Create session
session_id = await memory_manager.create_session(
    user_id=user_id,
    quiz_name="Python Quiz",
    quiz_type="multiple"
)

# Add answers
for i, question in enumerate(questions):
    user_answer = get_user_answer()  # Your logic
    correct_answer = question['correct']
    is_correct = user_answer == correct_answer

    await memory_manager.add_answer(
        user_id=user_id,
        question_id=i,
        question_text=question['text'],
        user_answer=user_answer,
        correct_answer=correct_answer,
        is_correct=is_correct
    )

# Complete session
results = await memory_manager.complete_session(user_id)
print(f"Score: {results['score']}")
print(f"Correct: {results['correct_answers']}/{results['total_questions']}")

# Get updated stats
stats = await memory_manager.get_user_stats(user_id)
print(f"Total Score: {stats['total_score']}")
```

### Checking Leaderboard

```python
# Get top 10
leaders = await memory_manager.get_leaderboard(limit=10)

for rank, leader in enumerate(leaders, 1):
    print(f"{rank}. {leader['username']}: {leader['total_score']} points")
```

### Managing User Data

```python
# Export user data
backup_manager = get_backup_manager()
export_path = backup_manager.export_user_data(user_id=12345)
print(f"Data exported to: {export_path}")

# Delete user data (GDPR)
await memory_manager.delete_user_data(user_id=12345)
```

## Performance Tuning

### Database Optimization

1. **Vacuum regularly** to defragment the database:
```python
import sqlite3
conn = sqlite3.connect('database/quiz_bot.db')
conn.execute('VACUUM')
conn.close()
```

2. **Analyze tables** for query optimization:
```sql
ANALYZE;
```

3. **Monitor query performance** using logging:
```python
from utils.logging_config import performance_logger

with TimedOperation("get_user_stats", performance_logger):
    stats = await memory_manager.get_user_stats(user_id)
```

### Cache Tuning

Adjust TTL values in `config.py`:

```python
CACHE_CONFIG = {
    'session_ttl': 1800,      # Increase for longer-lived sessions
    'user_ttl': 3600,          # Increase for more cache hits
    'leaderboard_ttl': 300,    # Decrease for fresher data
    'quiz_ttl': 1800,
    'stats_ttl': 600,
}
```

### Memory Management

Monitor cache size:

```python
cache_stats = cache.get_all_stats()
if cache_stats['user_cache']['size'] > 4000:
    cache.user_cache.clear()
```

## Troubleshooting

### Common Issues

#### 1. Database Locked

**Symptom**: `sqlite3.OperationalError: database is locked`

**Solution**:
- Ensure only one process accesses the database
- Use connection pooling
- Increase timeout: `sqlite3.connect(db_path, timeout=30)`

#### 2. Memory Growth

**Symptom**: High memory usage

**Solution**:
- Reduce cache sizes in `config.py`
- Decrease TTL values
- Call `cache.cleanup_all_expired()` more frequently

#### 3. Slow Queries

**Symptom**: Slow database operations

**Solution**:
- Check indexes are present
- Run `ANALYZE` to update statistics
- Review slow queries in `logs/database.log`
- Consider adding more indexes

#### 4. Cache Misses

**Symptom**: High cache miss rate

**Solution**:
- Increase cache size
- Increase TTL
- Preload frequently accessed data

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Check

```python
async def health_check():
    # Check database
    stats = backup_manager.get_database_stats()
    print(f"Database size: {stats['database_size_mb']} MB")
    print(f"Total users: {stats['users_count']}")

    # Check cache
    cache_stats = cache.get_all_stats()
    for cache_name, stats in cache_stats.items():
        print(f"{cache_name}: {stats['hit_rate']}% hit rate")
```

## Best Practices

1. **Always use async/await** for database operations
2. **Check cache before database** for read operations
3. **Invalidate cache** when data changes
4. **Use transactions** for multiple related operations
5. **Monitor performance** using logging
6. **Regular backups** - enable auto-backup scheduler
7. **Clean up old data** periodically
8. **Use indexes** for frequently queried fields
9. **Batch operations** when possible
10. **Handle errors gracefully** with try/except

## Migration Guide

### Upgrading from Version 1.0

The memory system is backward compatible. To migrate:

1. Install new dependencies:
```bash
pip install -r requirements.txt
```

2. Database will auto-migrate on first run

3. Update bot imports:
```python
from memory.memory_manager import MemoryManager
memory_manager = MemoryManager()
```

4. Add memory calls to existing code:
```python
# Before quiz
await memory_manager.load_user(user_id, username, first_name)

# During quiz
await memory_manager.add_answer(...)

# After quiz
await memory_manager.complete_session(user_id)
```
