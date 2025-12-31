"""
Backup and Data Export Utilities
Provides database backup and user data export functionality
"""

import os
import shutil
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import asyncio

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages database backups and data exports"""

    def __init__(self, db_path: str = "database/quiz_bot.db",
                 backup_dir: str = "backups"):
        """
        Initialize the backup manager

        Args:
            db_path: Path to the database file
            backup_dir: Directory to store backups
        """
        self.db_path = db_path
        self.backup_dir = backup_dir
        self._ensure_backup_dir()

    def _ensure_backup_dir(self):
        """Ensure the backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Created backup directory: {self.backup_dir}")

    def create_backup(self, backup_name: str = None) -> Optional[str]:
        """
        Create a backup of the database

        Args:
            backup_name: Optional custom backup name

        Returns:
            Path to the backup file or None if failed
        """
        try:
            if not os.path.exists(self.db_path):
                logger.warning(f"Database file not found: {self.db_path}")
                return None

            # Generate backup filename
            if backup_name is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"quiz_bot_backup_{timestamp}.db"

            backup_path = os.path.join(self.backup_dir, backup_name)

            # Copy database file
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Backup created: {backup_path}")

            return backup_path

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def restore_backup(self, backup_name: str) -> bool:
        """
        Restore database from a backup

        Args:
            backup_name: Name of the backup file to restore

        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = os.path.join(self.backup_dir, backup_name)

            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False

            # Create a backup of current database before restoring
            current_backup = self.create_backup("pre_restore_backup.db")
            if current_backup:
                logger.info(f"Created pre-restore backup: {current_backup}")

            # Restore the backup
            shutil.copy2(backup_path, self.db_path)
            logger.info(f"Database restored from: {backup_path}")

            return True

        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False

    def cleanup_old_backups(self, days: int = 7):
        """
        Delete backups older than specified days

        Args:
            days: Delete backups older than this many days
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0

            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.db'):
                    filepath = os.path.join(self.backup_dir, filename)
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))

                    if file_time < cutoff_date:
                        os.remove(filepath)
                        deleted_count += 1
                        logger.info(f"Deleted old backup: {filename}")

            logger.info(f"Cleaned up {deleted_count} old backup(s)")

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")

    def list_backups(self) -> list:
        """
        List all available backups

        Returns:
            List of backup filenames with their creation times
        """
        try:
            backups = []
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.db'):
                    filepath = os.path.join(self.backup_dir, filename)
                    created_at = datetime.fromtimestamp(os.path.getmtime(filepath))
                    size_mb = os.path.getsize(filepath) / (1024 * 1024)

                    backups.append({
                        'filename': filename,
                        'created_at': created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        'size_mb': round(size_mb, 2)
                    })

            # Sort by creation time, newest first
            backups.sort(key=lambda x: x['created_at'], reverse=True)
            return backups

        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    def export_user_data(self, user_id: int, export_path: str = None) -> Optional[str]:
        """
        Export all data for a specific user (GDPR compliance)

        Args:
            user_id: User identifier
            export_path: Optional custom export path

        Returns:
            Path to the exported JSON file or None if failed
        """
        try:
            if not os.path.exists(self.db_path):
                logger.warning(f"Database file not found: {self.db_path}")
                return None

            # Generate export filename
            if export_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = os.path.join(
                    self.backup_dir,
                    f"user_data_{user_id}_{timestamp}.json"
                )

            # Collect user data
            user_data = {
                'user_id': user_id,
                'export_date': datetime.now().isoformat(),
                'user_profile': None,
                'quiz_sessions': [],
                'quiz_answers': [],
                'preferences': None,
                'conversation_history': [],
                'achievements': []
            }

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Export user profile
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_data['user_profile'] = dict(row)

            # Export quiz sessions
            cursor.execute("SELECT * FROM quiz_sessions WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            user_data['quiz_sessions'] = [dict(row) for row in rows]

            # Export quiz answers for user's sessions
            session_ids = [s['session_id'] for s in user_data['quiz_sessions']]
            if session_ids:
                placeholders = ','.join('?' * len(session_ids))
                cursor.execute(
                    f"SELECT * FROM quiz_answers WHERE session_id IN ({placeholders})",
                    session_ids
                )
                rows = cursor.fetchall()
                user_data['quiz_answers'] = [dict(row) for row in rows]

            # Export preferences
            cursor.execute("SELECT * FROM user_preferences WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_data['preferences'] = dict(row)

            # Export conversation history
            cursor.execute("SELECT * FROM conversation_history WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            user_data['conversation_history'] = [dict(row) for row in rows]

            # Export achievements
            cursor.execute("SELECT * FROM user_achievements WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            user_data['achievements'] = [dict(row) for row in rows]

            conn.close()

            # Write to JSON file
            with open(export_path, 'w') as f:
                json.dump(user_data, f, indent=2, default=str)

            logger.info(f"User data exported: {export_path}")
            return export_path

        except Exception as e:
            logger.error(f"Error exporting user data: {e}")
            return None

    def get_database_stats(self) -> Dict:
        """
        Get statistics about the database

        Returns:
            Dictionary with database statistics
        """
        try:
            if not os.path.exists(self.db_path):
                return {'error': 'Database not found'}

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = {}

            # Get table row counts
            tables = ['users', 'quiz_sessions', 'quiz_answers', 'user_preferences',
                     'conversation_history', 'user_achievements', 'quiz_metadata']

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                stats[f'{table}_count'] = count

            # Get database size
            size_bytes = os.path.getsize(self.db_path)
            stats['database_size_mb'] = round(size_bytes / (1024 * 1024), 2)

            # Get most active users
            cursor.execute("""
                SELECT user_id, username, total_score, quizzes_taken
                FROM users
                ORDER BY total_score DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()
            stats['top_users'] = [
                {'user_id': r[0], 'username': r[1], 'score': r[2], 'quizzes': r[3]}
                for r in rows
            ]

            conn.close()
            return stats

        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {'error': str(e)}


class AutoBackupScheduler:
    """Automatically schedules regular backups"""

    def __init__(self, backup_manager: BackupManager, interval_hours: int = 24):
        """
        Initialize auto backup scheduler

        Args:
            backup_manager: BackupManager instance
            interval_hours: Backup interval in hours
        """
        self.backup_manager = backup_manager
        self.interval_hours = interval_hours
        self._running = False
        self._task = None

    async def start(self):
        """Start the automatic backup scheduler"""
        if self._running:
            logger.warning("Backup scheduler already running")
            return

        self._running = True
        logger.info(f"Starting automatic backup scheduler (every {self.interval_hours} hours)")

        async def backup_loop():
            while self._running:
                try:
                    # Create backup
                    backup_path = self.backup_manager.create_backup()
                    if backup_path:
                        logger.info(f"Automatic backup created: {backup_path}")

                    # Cleanup old backups (keep last 7 days)
                    self.backup_manager.cleanup_old_backups(days=7)

                    # Wait for next backup
                    await asyncio.sleep(self.interval_hours * 3600)

                except Exception as e:
                    logger.error(f"Error in backup scheduler: {e}")
                    await asyncio.sleep(3600)  # Retry after 1 hour on error

        self._task = asyncio.create_task(backup_loop())

    def stop(self):
        """Stop the automatic backup scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Backup scheduler stopped")


# Global backup manager instance
_backup_manager = None


def get_backup_manager(db_path: str = "database/quiz_bot.db") -> BackupManager:
    """Get or create the global backup manager instance"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(db_path)
    return _backup_manager
