-- Database Schema for Quiz Bot Memory System
-- SQLite database for storing user data, quiz sessions, and statistics

-- Users table: Store user profiles
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    discord_id TEXT UNIQUE,
    telegram_id TEXT UNIQUE,
    username TEXT,
    first_name TEXT,
    join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_score INTEGER DEFAULT 0,
    quizzes_taken INTEGER DEFAULT 0,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Quiz sessions table: Track quiz attempts
CREATE TABLE IF NOT EXISTS quiz_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    quiz_name TEXT NOT NULL,
    quiz_type TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    score INTEGER DEFAULT 0,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    time_taken REAL,
    status TEXT DEFAULT 'in_progress',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Quiz answers table: Store individual answers
CREATE TABLE IF NOT EXISTS quiz_answers (
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER,
    question_text TEXT,
    user_answer TEXT,
    correct_answer TEXT,
    is_correct BOOLEAN,
    time_taken REAL,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES quiz_sessions(session_id)
);

-- User preferences table: Save user settings
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id INTEGER PRIMARY KEY,
    difficulty_preference TEXT DEFAULT 'medium',
    category_preference TEXT,
    notification_enabled BOOLEAN DEFAULT 1,
    auto_difficulty BOOLEAN DEFAULT 1,
    theme TEXT DEFAULT 'default',
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Conversation history table: Track recent interactions
CREATE TABLE IF NOT EXISTS conversation_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message_type TEXT,
    message_text TEXT,
    context TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Leaderboard cache table: Store computed rankings
CREATE TABLE IF NOT EXISTS leaderboard_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    leaderboard_type TEXT NOT NULL,
    category TEXT,
    data TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User achievements table: Track milestones and badges
CREATE TABLE IF NOT EXISTS user_achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_type TEXT NOT NULL,
    achievement_name TEXT NOT NULL,
    description TEXT,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Quiz metadata table: Store information about created quizzes
CREATE TABLE IF NOT EXISTS quiz_metadata (
    quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_name TEXT UNIQUE NOT NULL,
    creator_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_questions INTEGER,
    time_gap INTEGER,
    status TEXT DEFAULT 'active',
    times_played INTEGER DEFAULT 0,
    average_score REAL DEFAULT 0,
    FOREIGN KEY (creator_id) REFERENCES users(user_id)
);

-- Indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_user_sessions ON quiz_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_session_answers ON quiz_answers(session_id);
CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversation_history(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_type ON leaderboard_cache(leaderboard_type);
CREATE INDEX IF NOT EXISTS idx_quiz_creator ON quiz_metadata(creator_id);
CREATE INDEX IF NOT EXISTS idx_user_achievements ON user_achievements(user_id);
CREATE INDEX IF NOT EXISTS idx_session_status ON quiz_sessions(status);
CREATE INDEX IF NOT EXISTS idx_user_last_active ON users(last_active);
