"""
Memory Manager Module
Main interface for managing bot memory including sessions, users, and conversations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class SessionMemory:
    """Manages active quiz session memory"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.active_sessions: Dict[int, Dict] = {}  # user_id -> session data

    async def create_session(self, user_id: int, quiz_name: str,
                            quiz_type: str = None) -> Optional[int]:
        """
        Create a new quiz session

        Args:
            user_id: User identifier
            quiz_name: Name of the quiz
            quiz_type: Type of quiz (single/multiple)

        Returns:
            Session ID or None
        """
        session_id = await self.db_manager.create_session(user_id, quiz_name, quiz_type)
        if session_id:
            self.active_sessions[user_id] = {
                'session_id': session_id,
                'quiz_name': quiz_name,
                'quiz_type': quiz_type,
                'current_question': 0,
                'correct_answers': 0,
                'total_questions': 0,
                'answers': [],
                'start_time': datetime.now()
            }
            logger.info(f"Created session {session_id} for user {user_id}")
        return session_id

    async def add_answer(self, user_id: int, question_id: int,
                        question_text: str, user_answer: str,
                        correct_answer: str, is_correct: bool):
        """
        Add an answer to the current session

        Args:
            user_id: User identifier
            question_id: Question identifier
            question_text: The question text
            user_answer: User's answer
            correct_answer: The correct answer
            is_correct: Whether the answer was correct
        """
        if user_id not in self.active_sessions:
            logger.warning(f"No active session for user {user_id}")
            return

        session = self.active_sessions[user_id]
        session_id = session['session_id']

        # Calculate time taken
        time_taken = (datetime.now() - session['start_time']).total_seconds()

        # Save to database
        await self.db_manager.save_answer(
            session_id, question_id, question_text,
            user_answer, correct_answer, is_correct, time_taken
        )

        # Update in-memory session
        session['answers'].append({
            'question_id': question_id,
            'user_answer': user_answer,
            'is_correct': is_correct,
            'time_taken': time_taken
        })
        session['current_question'] += 1
        session['total_questions'] += 1
        if is_correct:
            session['correct_answers'] += 1

        logger.info(f"Added answer for user {user_id}, session {session_id}")

    async def get_session(self, user_id: int) -> Optional[Dict]:
        """Get active session for a user"""
        return self.active_sessions.get(user_id)

    async def complete_session(self, user_id: int) -> Dict:
        """
        Complete a quiz session and calculate results

        Args:
            user_id: User identifier

        Returns:
            Session results dictionary
        """
        if user_id not in self.active_sessions:
            logger.warning(f"No active session to complete for user {user_id}")
            return {}

        session = self.active_sessions[user_id]
        session_id = session['session_id']

        # Calculate score and statistics
        correct = session['correct_answers']
        total = session['total_questions']
        score = int((correct / total * 100)) if total > 0 else 0

        # Update database
        await self.db_manager.update_session(
            session_id,
            score=score,
            correct_answers=correct,
            total_questions=total,
            status='completed'
        )

        # Update user's total score
        await self.db_manager.update_user_score(user_id, score)

        # Get results
        results = {
            'session_id': session_id,
            'quiz_name': session['quiz_name'],
            'score': score,
            'correct_answers': correct,
            'total_questions': total,
            'percentage': round(correct / total * 100, 2) if total > 0 else 0
        }

        # Remove from active sessions
        del self.active_sessions[user_id]

        logger.info(f"Completed session {session_id} for user {user_id}: {score} points")
        return results

    async def pause_session(self, user_id: int):
        """Pause an active session"""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            await self.db_manager.update_session(session['session_id'], status='paused')
            logger.info(f"Paused session for user {user_id}")

    async def resume_session(self, user_id: int):
        """Resume a paused session"""
        if user_id in self.active_sessions:
            session = self.active_sessions[user_id]
            await self.db_manager.update_session(session['session_id'], status='in_progress')
            logger.info(f"Resumed session for user {user_id}")

    def clear_session(self, user_id: int):
        """Clear session from memory without saving"""
        if user_id in self.active_sessions:
            del self.active_sessions[user_id]
            logger.info(f"Cleared session for user {user_id}")


class UserMemory:
    """Manages user-specific memory and data"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.user_cache: Dict[int, Dict] = {}  # user_id -> cached user data
        self.cache_ttl = timedelta(hours=1)
        self.cache_timestamps: Dict[int, datetime] = {}

    async def load_user(self, user_id: int, username: str = None,
                       first_name: str = None, telegram_id: str = None) -> Dict:
        """
        Load user profile, creating if necessary

        Args:
            user_id: User identifier
            username: User's username
            first_name: User's first name
            telegram_id: Telegram user ID

        Returns:
            User data dictionary
        """
        # Check cache first
        if user_id in self.user_cache:
            if datetime.now() - self.cache_timestamps[user_id] < self.cache_ttl:
                return self.user_cache[user_id]

        # Create/update user in database
        await self.db_manager.create_user(user_id, username, first_name, telegram_id)

        # Load from database
        user = await self.db_manager.get_user(user_id)
        if user:
            self.user_cache[user_id] = user
            self.cache_timestamps[user_id] = datetime.now()
            return user

        return {}

    async def get_user_stats(self, user_id: int) -> Dict:
        """
        Get comprehensive user statistics

        Args:
            user_id: User identifier

        Returns:
            Statistics dictionary
        """
        return await self.db_manager.get_user_statistics(user_id)

    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """
        Get user's quiz history

        Args:
            user_id: User identifier
            limit: Number of sessions to retrieve

        Returns:
            List of session dictionaries
        """
        return await self.db_manager.get_user_sessions(user_id, limit)

    async def update_preferences(self, user_id: int, **preferences):
        """
        Update user preferences

        Args:
            user_id: User identifier
            **preferences: Preference key-value pairs
        """
        await self.db_manager.set_preferences(user_id, **preferences)
        # Invalidate cache
        if user_id in self.user_cache:
            del self.user_cache[user_id]
            del self.cache_timestamps[user_id]

    async def get_preferences(self, user_id: int) -> Dict:
        """Get user preferences"""
        prefs = await self.db_manager.get_preferences(user_id)
        return prefs or {}

    def clear_cache(self, user_id: int = None):
        """Clear user cache"""
        if user_id:
            if user_id in self.user_cache:
                del self.user_cache[user_id]
                del self.cache_timestamps[user_id]
        else:
            self.user_cache.clear()
            self.cache_timestamps.clear()


class ConversationMemory:
    """Manages conversation history and context"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.recent_conversations: Dict[int, List[Dict]] = {}  # user_id -> conversation list
        self.max_memory = 10  # Keep last 10 interactions in memory

    async def add_message(self, user_id: int, message_type: str,
                         message_text: str, context: str = None):
        """
        Add a message to conversation history

        Args:
            user_id: User identifier
            message_type: Type of message (command, response, etc.)
            message_text: The message text
            context: Additional context
        """
        await self.db_manager.add_conversation(user_id, message_type, message_text, context)

        # Update in-memory cache
        if user_id not in self.recent_conversations:
            self.recent_conversations[user_id] = []

        self.recent_conversations[user_id].append({
            'message_type': message_type,
            'message_text': message_text,
            'context': context,
            'timestamp': datetime.now()
        })

        # Keep only recent conversations in memory
        if len(self.recent_conversations[user_id]) > self.max_memory:
            self.recent_conversations[user_id] = self.recent_conversations[user_id][-self.max_memory:]

    async def get_context(self, user_id: int, limit: int = 5) -> List[Dict]:
        """
        Get recent conversation context

        Args:
            user_id: User identifier
            limit: Number of messages to retrieve

        Returns:
            List of conversation dictionaries
        """
        # Try memory first
        if user_id in self.recent_conversations:
            return self.recent_conversations[user_id][-limit:]

        # Fall back to database
        history = await self.db_manager.get_conversation_history(user_id, limit)
        return history

    def clear_context(self, user_id: int):
        """Clear conversation context for a user"""
        if user_id in self.recent_conversations:
            del self.recent_conversations[user_id]


class MemoryManager:
    """Main memory manager interface"""

    def __init__(self, db_path: str = "database/quiz_bot.db"):
        """
        Initialize the memory manager

        Args:
            db_path: Path to the database file
        """
        self.db_manager = DatabaseManager(db_path)
        self.session_memory = SessionMemory(self.db_manager)
        self.user_memory = UserMemory(self.db_manager)
        self.conversation_memory = ConversationMemory(self.db_manager)
        logger.info("MemoryManager initialized")

    # Session operations
    async def create_session(self, user_id: int, quiz_name: str, quiz_type: str = None) -> Optional[int]:
        """Create a new quiz session"""
        return await self.session_memory.create_session(user_id, quiz_name, quiz_type)

    async def add_answer(self, user_id: int, question_id: int, question_text: str,
                        user_answer: str, correct_answer: str, is_correct: bool):
        """Add an answer to the current session"""
        await self.session_memory.add_answer(user_id, question_id, question_text,
                                             user_answer, correct_answer, is_correct)

    async def complete_session(self, user_id: int) -> Dict:
        """Complete a quiz session"""
        return await self.session_memory.complete_session(user_id)

    async def get_active_session(self, user_id: int) -> Optional[Dict]:
        """Get active session for a user"""
        return await self.session_memory.get_session(user_id)

    # User operations
    async def load_user(self, user_id: int, username: str = None,
                       first_name: str = None, telegram_id: str = None) -> Dict:
        """Load or create user profile"""
        return await self.user_memory.load_user(user_id, username, first_name, telegram_id)

    async def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        return await self.user_memory.get_user_stats(user_id)

    async def get_user_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user quiz history"""
        return await self.user_memory.get_user_history(user_id, limit)

    async def update_user_preferences(self, user_id: int, **preferences):
        """Update user preferences"""
        await self.user_memory.update_preferences(user_id, **preferences)

    async def get_user_preferences(self, user_id: int) -> Dict:
        """Get user preferences"""
        return await self.user_memory.get_preferences(user_id)

    # Conversation operations
    async def add_conversation(self, user_id: int, message_type: str,
                              message_text: str, context: str = None):
        """Add a conversation entry"""
        await self.conversation_memory.add_message(user_id, message_type, message_text, context)

    async def get_conversation_context(self, user_id: int, limit: int = 5) -> List[Dict]:
        """Get recent conversation context"""
        return await self.conversation_memory.get_context(user_id, limit)

    # Leaderboard operations
    async def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get global leaderboard"""
        return await self.db_manager.get_leaderboard(limit)

    # Quiz metadata operations
    async def save_quiz_metadata(self, quiz_name: str, creator_id: int,
                                total_questions: int, time_gap: int):
        """Save quiz metadata"""
        await self.db_manager.create_quiz_metadata(quiz_name, creator_id,
                                                   total_questions, time_gap)

    async def update_quiz_played(self, quiz_name: str):
        """Update quiz play count"""
        await self.db_manager.update_quiz_stats(quiz_name)

    # Achievements
    async def add_achievement(self, user_id: int, achievement_type: str,
                             achievement_name: str, description: str = None):
        """Add an achievement"""
        await self.db_manager.add_achievement(user_id, achievement_type,
                                             achievement_name, description)

    async def get_achievements(self, user_id: int) -> List[Dict]:
        """Get user achievements"""
        return await self.db_manager.get_user_achievements(user_id)

    # Utility operations
    async def delete_user_data(self, user_id: int):
        """Delete all user data"""
        await self.db_manager.delete_user_data(user_id)
        self.session_memory.clear_session(user_id)
        self.user_memory.clear_cache(user_id)
        self.conversation_memory.clear_context(user_id)

    def clear_caches(self):
        """Clear all in-memory caches"""
        self.user_memory.clear_cache()
        self.conversation_memory.recent_conversations.clear()
