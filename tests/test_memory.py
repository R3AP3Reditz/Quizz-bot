"""
Test suite for memory system
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager
from memory.memory_manager import MemoryManager, SessionMemory, UserMemory, ConversationMemory
from memory.cache import LRUCache, MemoryCache
from utils.backup import BackupManager


# ==================== Database Manager Tests ====================

@pytest.fixture
async def db_manager():
    """Create a test database manager"""
    test_db_path = "database/test_quiz_bot.db"
    db = DatabaseManager(test_db_path)
    yield db
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.mark.asyncio
async def test_create_user(db_manager):
    """Test user creation"""
    success = await db_manager.create_user(
        user_id=12345,
        username="testuser",
        first_name="Test",
        telegram_id="12345"
    )
    assert success is True

    user = await db_manager.get_user(12345)
    assert user is not None
    assert user['username'] == "testuser"
    assert user['first_name'] == "Test"


@pytest.mark.asyncio
async def test_create_session(db_manager):
    """Test quiz session creation"""
    # Create user first
    await db_manager.create_user(12345, "testuser", "Test", "12345")

    # Create session
    session_id = await db_manager.create_session(12345, "Test Quiz", "single")
    assert session_id is not None
    assert isinstance(session_id, int)


@pytest.mark.asyncio
async def test_update_session(db_manager):
    """Test session updates"""
    await db_manager.create_user(12345, "testuser", "Test", "12345")
    session_id = await db_manager.create_session(12345, "Test Quiz")

    await db_manager.update_session(
        session_id,
        score=85,
        correct_answers=17,
        total_questions=20,
        status='completed'
    )

    # Verify update
    sessions = await db_manager.get_user_sessions(12345)
    assert len(sessions) > 0
    assert sessions[0]['score'] == 85
    assert sessions[0]['status'] == 'completed'


@pytest.mark.asyncio
async def test_save_answer(db_manager):
    """Test saving quiz answers"""
    await db_manager.create_user(12345, "testuser", "Test", "12345")
    session_id = await db_manager.create_session(12345, "Test Quiz")

    await db_manager.save_answer(
        session_id=session_id,
        question_id=1,
        question_text="What is 2+2?",
        user_answer="4",
        correct_answer="4",
        is_correct=True,
        time_taken=5.5
    )

    answers = await db_manager.get_session_answers(session_id)
    assert len(answers) == 1
    assert answers[0]['is_correct'] is True


@pytest.mark.asyncio
async def test_user_preferences(db_manager):
    """Test user preferences"""
    await db_manager.create_user(12345, "testuser", "Test", "12345")

    await db_manager.set_preferences(
        12345,
        difficulty_preference='hard',
        notification_enabled=True
    )

    prefs = await db_manager.get_preferences(12345)
    assert prefs is not None
    assert prefs['difficulty_preference'] == 'hard'
    assert prefs['notification_enabled'] == 1


@pytest.mark.asyncio
async def test_leaderboard(db_manager):
    """Test leaderboard functionality"""
    # Create multiple users
    for i in range(5):
        await db_manager.create_user(
            user_id=1000 + i,
            username=f"user{i}",
            first_name=f"User{i}"
        )
        await db_manager.update_user_score(1000 + i, (i + 1) * 10)

    leaderboard = await db_manager.get_leaderboard(limit=5)
    assert len(leaderboard) == 5
    # Check if sorted by score descending
    assert leaderboard[0]['total_score'] >= leaderboard[1]['total_score']


@pytest.mark.asyncio
async def test_conversation_history(db_manager):
    """Test conversation history"""
    await db_manager.create_user(12345, "testuser", "Test", "12345")

    for i in range(5):
        await db_manager.add_conversation(
            user_id=12345,
            message_type='command',
            message_text=f'/test{i}',
            context=f'Test context {i}'
        )

    history = await db_manager.get_conversation_history(12345, limit=5)
    assert len(history) == 5


@pytest.mark.asyncio
async def test_delete_user_data(db_manager):
    """Test user data deletion"""
    await db_manager.create_user(12345, "testuser", "Test", "12345")
    session_id = await db_manager.create_session(12345, "Test Quiz")

    await db_manager.delete_user_data(12345)

    user = await db_manager.get_user(12345)
    assert user is None

    sessions = await db_manager.get_user_sessions(12345)
    assert len(sessions) == 0


# ==================== Memory Manager Tests ====================

@pytest.fixture
async def memory_manager():
    """Create a test memory manager"""
    test_db_path = "database/test_memory.db"
    mm = MemoryManager(test_db_path)
    yield mm
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.mark.asyncio
async def test_memory_create_session(memory_manager):
    """Test session creation through memory manager"""
    await memory_manager.load_user(12345, "testuser", "Test")

    session_id = await memory_manager.create_session(12345, "Memory Test Quiz")
    assert session_id is not None

    active_session = await memory_manager.get_active_session(12345)
    assert active_session is not None
    assert active_session['quiz_name'] == "Memory Test Quiz"


@pytest.mark.asyncio
async def test_memory_add_answer(memory_manager):
    """Test adding answers through memory manager"""
    await memory_manager.load_user(12345, "testuser", "Test")
    await memory_manager.create_session(12345, "Test Quiz")

    await memory_manager.add_answer(
        user_id=12345,
        question_id=1,
        question_text="Test question?",
        user_answer="A",
        correct_answer="A",
        is_correct=True
    )

    session = await memory_manager.get_active_session(12345)
    assert session['correct_answers'] == 1
    assert session['total_questions'] == 1


@pytest.mark.asyncio
async def test_memory_complete_session(memory_manager):
    """Test session completion"""
    await memory_manager.load_user(12345, "testuser", "Test")
    await memory_manager.create_session(12345, "Test Quiz")

    # Add some answers
    for i in range(10):
        await memory_manager.add_answer(
            user_id=12345,
            question_id=i,
            question_text=f"Question {i}?",
            user_answer="A",
            correct_answer="A" if i % 2 == 0 else "B",
            is_correct=(i % 2 == 0)
        )

    results = await memory_manager.complete_session(12345)
    assert results is not None
    assert results['score'] == 50  # 5 correct out of 10
    assert results['correct_answers'] == 5


@pytest.mark.asyncio
async def test_memory_user_stats(memory_manager):
    """Test user statistics"""
    await memory_manager.load_user(12345, "testuser", "Test")

    # Create and complete a session
    await memory_manager.create_session(12345, "Test Quiz")
    await memory_manager.add_answer(12345, 1, "Q1?", "A", "A", True)
    await memory_manager.complete_session(12345)

    stats = await memory_manager.get_user_stats(12345)
    assert stats is not None
    assert stats['quizzes_taken'] >= 1


# ==================== Cache Tests ====================

def test_lru_cache_basic():
    """Test basic LRU cache operations"""
    cache = LRUCache(max_size=3, default_ttl=0)  # No TTL for testing

    cache.set('key1', 'value1')
    cache.set('key2', 'value2')
    cache.set('key3', 'value3')

    assert cache.get('key1') == 'value1'
    assert cache.get('key2') == 'value2'
    assert cache.get('key3') == 'value3'


def test_lru_cache_eviction():
    """Test LRU cache eviction"""
    cache = LRUCache(max_size=2, default_ttl=0)

    cache.set('key1', 'value1')
    cache.set('key2', 'value2')
    cache.set('key3', 'value3')  # Should evict key1

    assert cache.get('key1') is None
    assert cache.get('key2') == 'value2'
    assert cache.get('key3') == 'value3'


def test_lru_cache_ttl():
    """Test cache TTL"""
    import time
    cache = LRUCache(max_size=10, default_ttl=1)  # 1 second TTL

    cache.set('key1', 'value1')
    assert cache.get('key1') == 'value1'

    time.sleep(1.5)
    assert cache.get('key1') is None  # Should be expired


def test_memory_cache():
    """Test memory cache manager"""
    cache = MemoryCache()

    # Test session cache
    cache.set_session(12345, {'quiz': 'test'})
    session = cache.get_session(12345)
    assert session is not None
    assert session['quiz'] == 'test'

    # Test user cache
    cache.set_user(12345, {'name': 'testuser'})
    user = cache.get_user(12345)
    assert user is not None
    assert user['name'] == 'testuser'


# ==================== Backup Tests ====================

@pytest.fixture
def backup_manager():
    """Create a test backup manager"""
    test_db_path = "database/test_backup.db"
    test_backup_dir = "test_backups"

    # Create test database
    with open(test_db_path, 'w') as f:
        f.write("test database")

    bm = BackupManager(test_db_path, test_backup_dir)
    yield bm

    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    if os.path.exists(test_backup_dir):
        import shutil
        shutil.rmtree(test_backup_dir)


def test_create_backup(backup_manager):
    """Test backup creation"""
    backup_path = backup_manager.create_backup("test_backup.db")
    assert backup_path is not None
    assert os.path.exists(backup_path)


def test_list_backups(backup_manager):
    """Test listing backups"""
    backup_manager.create_backup("backup1.db")
    backup_manager.create_backup("backup2.db")

    backups = backup_manager.list_backups()
    assert len(backups) >= 2


def test_cleanup_old_backups(backup_manager):
    """Test cleanup of old backups"""
    backup_manager.create_backup("old_backup.db")
    # In a real test, you'd modify the file timestamp
    backup_manager.cleanup_old_backups(days=0)


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
