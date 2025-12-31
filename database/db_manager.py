"""
Database Manager Module
Handles all database operations for the quiz bot memory system
"""

import aiosqlite
import sqlite3
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""

    def __init__(self, db_path: str = "database/quiz_bot.db"):
        """
        Initialize the database manager

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_directory()
        self._init_database()

    def _ensure_directory(self):
        """Ensure the database directory exists"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Created database directory: {db_dir}")

    def _init_database(self):
        """Initialize the database with schema if it doesn't exist"""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

            with sqlite3.connect(self.db_path) as conn:
                if os.path.exists(schema_path):
                    with open(schema_path, 'r') as f:
                        schema = f.read()
                    conn.executescript(schema)
                    conn.commit()
                    logger.info("Database initialized successfully")
                else:
                    logger.warning(f"Schema file not found: {schema_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    async def get_connection(self):
        """Get an async database connection"""
        return await aiosqlite.connect(self.db_path)

    # ==================== User Operations ====================

    async def create_user(self, user_id: int, username: str = None,
                         first_name: str = None, telegram_id: str = None) -> bool:
        """
        Create a new user or update if exists

        Args:
            user_id: Unique user identifier
            username: User's username
            first_name: User's first name
            telegram_id: Telegram user ID

        Returns:
            True if successful, False otherwise
        """
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    INSERT INTO users (user_id, username, first_name, telegram_id, join_date, last_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        username = COALESCE(excluded.username, username),
                        first_name = COALESCE(excluded.first_name, first_name),
                        last_active = excluded.last_active
                """, (user_id, username, first_name, telegram_id,
                      datetime.now(), datetime.now()))
                await db.commit()
                logger.info(f"User created/updated: {user_id}")
                return True
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        """
        Get user profile by ID

        Args:
            user_id: User identifier

        Returns:
            User data as dictionary or None
        """
        try:
            async with await self.get_connection() as db:
                async with db.execute(
                    "SELECT * FROM users WHERE user_id = ?", (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [desc[0] for desc in cursor.description]
                        return dict(zip(columns, row))
                    return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    async def update_user_score(self, user_id: int, score_delta: int):
        """Update user's total score"""
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    UPDATE users
                    SET total_score = total_score + ?,
                        quizzes_taken = quizzes_taken + 1,
                        last_active = ?
                    WHERE user_id = ?
                """, (score_delta, datetime.now(), user_id))
                await db.commit()
        except Exception as e:
            logger.error(f"Error updating user score: {e}")

    # ==================== Quiz Session Operations ====================

    async def create_session(self, user_id: int, quiz_name: str,
                            quiz_type: str = None) -> Optional[int]:
        """
        Create a new quiz session

        Args:
            user_id: User identifier
            quiz_name: Name of the quiz
            quiz_type: Type of quiz

        Returns:
            Session ID or None
        """
        try:
            async with await self.get_connection() as db:
                cursor = await db.execute("""
                    INSERT INTO quiz_sessions
                    (user_id, quiz_name, quiz_type, start_time, status)
                    VALUES (?, ?, ?, ?, 'in_progress')
                """, (user_id, quiz_name, quiz_type, datetime.now()))
                await db.commit()
                session_id = cursor.lastrowid
                logger.info(f"Session created: {session_id}")
                return session_id
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

    async def update_session(self, session_id: int, score: int = None,
                           correct_answers: int = None, total_questions: int = None,
                           status: str = None):
        """Update quiz session details"""
        try:
            updates = []
            params = []

            if score is not None:
                updates.append("score = ?")
                params.append(score)
            if correct_answers is not None:
                updates.append("correct_answers = ?")
                params.append(correct_answers)
            if total_questions is not None:
                updates.append("total_questions = ?")
                params.append(total_questions)
            if status:
                updates.append("status = ?")
                params.append(status)
                if status == 'completed':
                    updates.append("end_time = ?")
                    params.append(datetime.now())

            if updates:
                params.append(session_id)
                query = f"UPDATE quiz_sessions SET {', '.join(updates)} WHERE session_id = ?"

                async with await self.get_connection() as db:
                    await db.execute(query, params)
                    await db.commit()
        except Exception as e:
            logger.error(f"Error updating session: {e}")

    async def get_user_sessions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent quiz sessions for a user"""
        try:
            async with await self.get_connection() as db:
                async with db.execute("""
                    SELECT * FROM quiz_sessions
                    WHERE user_id = ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (user_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user sessions: {e}")
            return []

    # ==================== Quiz Answer Operations ====================

    async def save_answer(self, session_id: int, question_id: int,
                         question_text: str, user_answer: str,
                         correct_answer: str, is_correct: bool,
                         time_taken: float = None):
        """Save a quiz answer"""
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    INSERT INTO quiz_answers
                    (session_id, question_id, question_text, user_answer,
                     correct_answer, is_correct, time_taken, answered_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (session_id, question_id, question_text, user_answer,
                      correct_answer, is_correct, time_taken, datetime.now()))
                await db.commit()
        except Exception as e:
            logger.error(f"Error saving answer: {e}")

    async def get_session_answers(self, session_id: int) -> List[Dict]:
        """Get all answers for a quiz session"""
        try:
            async with await self.get_connection() as db:
                async with db.execute("""
                    SELECT * FROM quiz_answers
                    WHERE session_id = ?
                    ORDER BY answered_at
                """, (session_id,)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting session answers: {e}")
            return []

    # ==================== User Preferences Operations ====================

    async def get_preferences(self, user_id: int) -> Optional[Dict]:
        """Get user preferences"""
        try:
            async with await self.get_connection() as db:
                async with db.execute("""
                    SELECT * FROM user_preferences WHERE user_id = ?
                """, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [desc[0] for desc in cursor.description]
                        return dict(zip(columns, row))
                    return None
        except Exception as e:
            logger.error(f"Error getting preferences: {e}")
            return None

    async def set_preferences(self, user_id: int, **preferences):
        """Set user preferences"""
        try:
            async with await self.get_connection() as db:
                # Create default preferences if they don't exist
                await db.execute("""
                    INSERT OR IGNORE INTO user_preferences (user_id)
                    VALUES (?)
                """, (user_id,))

                # Update preferences
                updates = []
                params = []
                for key, value in preferences.items():
                    if key in ['difficulty_preference', 'category_preference',
                              'notification_enabled', 'auto_difficulty', 'theme']:
                        updates.append(f"{key} = ?")
                        params.append(value)

                if updates:
                    params.append(user_id)
                    query = f"UPDATE user_preferences SET {', '.join(updates)} WHERE user_id = ?"
                    await db.execute(query, params)
                    await db.commit()
        except Exception as e:
            logger.error(f"Error setting preferences: {e}")

    # ==================== Conversation History Operations ====================

    async def add_conversation(self, user_id: int, message_type: str,
                              message_text: str, context: str = None):
        """Add a conversation entry"""
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    INSERT INTO conversation_history
                    (user_id, message_type, message_text, context, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, message_type, message_text, context, datetime.now()))
                await db.commit()

                # Keep only last 20 conversations per user
                await db.execute("""
                    DELETE FROM conversation_history
                    WHERE user_id = ? AND history_id NOT IN (
                        SELECT history_id FROM conversation_history
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT 20
                    )
                """, (user_id, user_id))
                await db.commit()
        except Exception as e:
            logger.error(f"Error adding conversation: {e}")

    async def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        try:
            async with await self.get_connection() as db:
                async with db.execute("""
                    SELECT * FROM conversation_history
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (user_id, limit)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    # ==================== Leaderboard Operations ====================

    async def get_leaderboard(self, limit: int = 10, category: str = None) -> List[Dict]:
        """Get global leaderboard"""
        try:
            async with await self.get_connection() as db:
                query = """
                    SELECT user_id, username, first_name, total_score, quizzes_taken
                    FROM users
                    ORDER BY total_score DESC, quizzes_taken ASC
                    LIMIT ?
                """
                async with db.execute(query, (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []

    # ==================== Quiz Metadata Operations ====================

    async def create_quiz_metadata(self, quiz_name: str, creator_id: int,
                                   total_questions: int, time_gap: int):
        """Create quiz metadata"""
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    INSERT OR REPLACE INTO quiz_metadata
                    (quiz_name, creator_id, total_questions, time_gap, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (quiz_name, creator_id, total_questions, time_gap, datetime.now()))
                await db.commit()
        except Exception as e:
            logger.error(f"Error creating quiz metadata: {e}")

    async def update_quiz_stats(self, quiz_name: str):
        """Update quiz statistics after completion"""
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    UPDATE quiz_metadata
                    SET times_played = times_played + 1
                    WHERE quiz_name = ?
                """, (quiz_name,))
                await db.commit()
        except Exception as e:
            logger.error(f"Error updating quiz stats: {e}")

    # ==================== Achievements Operations ====================

    async def add_achievement(self, user_id: int, achievement_type: str,
                             achievement_name: str, description: str = None):
        """Add an achievement for a user"""
        try:
            async with await self.get_connection() as db:
                await db.execute("""
                    INSERT INTO user_achievements
                    (user_id, achievement_type, achievement_name, description, earned_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, achievement_type, achievement_name, description, datetime.now()))
                await db.commit()
        except Exception as e:
            logger.error(f"Error adding achievement: {e}")

    async def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Get all achievements for a user"""
        try:
            async with await self.get_connection() as db:
                async with db.execute("""
                    SELECT * FROM user_achievements
                    WHERE user_id = ?
                    ORDER BY earned_at DESC
                """, (user_id,)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            return []

    # ==================== Utility Operations ====================

    async def delete_user_data(self, user_id: int):
        """Delete all data for a user (GDPR compliance)"""
        try:
            async with await self.get_connection() as db:
                # Delete from all tables
                await db.execute("DELETE FROM quiz_answers WHERE session_id IN (SELECT session_id FROM quiz_sessions WHERE user_id = ?)", (user_id,))
                await db.execute("DELETE FROM quiz_sessions WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM conversation_history WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM user_achievements WHERE user_id = ?", (user_id,))
                await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
                await db.commit()
                logger.info(f"Deleted all data for user: {user_id}")
        except Exception as e:
            logger.error(f"Error deleting user data: {e}")

    async def get_user_statistics(self, user_id: int) -> Dict:
        """Get comprehensive statistics for a user"""
        try:
            async with await self.get_connection() as db:
                # Get basic user stats
                user = await self.get_user(user_id)
                if not user:
                    return {}

                # Get session stats
                async with db.execute("""
                    SELECT
                        COUNT(*) as total_sessions,
                        AVG(score) as avg_score,
                        MAX(score) as best_score,
                        SUM(correct_answers) as total_correct,
                        SUM(total_questions) as total_answered
                    FROM quiz_sessions
                    WHERE user_id = ? AND status = 'completed'
                """, (user_id,)) as cursor:
                    stats = await cursor.fetchone()
                    if stats:
                        return {
                            'user_id': user_id,
                            'username': user['username'],
                            'first_name': user['first_name'],
                            'total_score': user['total_score'],
                            'quizzes_taken': user['quizzes_taken'],
                            'total_sessions': stats[0] or 0,
                            'average_score': round(stats[1], 2) if stats[1] else 0,
                            'best_score': stats[2] or 0,
                            'total_correct': stats[3] or 0,
                            'total_answered': stats[4] or 0,
                            'join_date': user['join_date'],
                            'last_active': user['last_active']
                        }
                return {}
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return {}
