"""
Quiz Bot with Memory Integration
Enhanced version of the quiz bot with persistent memory and statistics
"""

import asyncio
import logging
import time
import random
from telegram.constants import ParseMode, ChatAction
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ConversationHandler, PollAnswerHandler, filters, CallbackQueryHandler

# Import memory system
from memory.memory_manager import MemoryManager
from memory.cache import get_cache
from utils.backup import get_backup_manager, AutoBackupScheduler

# Use your actual bot token here
bot_token = '7518438812:AAF29rspjnbm48FQMZXJBCTOL1U5HOUJC-4'

# Initialize memory system
memory_manager = MemoryManager()
cache = get_cache()
backup_manager = get_backup_manager()

# Quiz states
(ASK_NAME, ASK_QUESTION_TYPE, ASK_QUESTION, ASK_OPTIONS, ASK_ANSWER, ASK_TIME_GAP, ADD_MORE_QUESTIONS, ASK_START_TIMER) = range(8)

# Quiz management
quizzes = {}  # Store quizzes globally
quiz_participants = {}  # Track group participants
quiz_results = {}  # Store quiz results
user_quizzes = {}  # Store all quizzes created by a user

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== Start Command with Memory ====================
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user

    # Load user from memory (creates if new)
    user_data = await memory_manager.load_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        telegram_id=str(user.id)
    )

    # Log conversation
    await memory_manager.add_conversation(
        user_id=user.id,
        message_type='command',
        message_text='/start',
        context='User started bot'
    )

    # Display typing action
    await context.bot.send_chat_action(chat_id=user.id, action=ChatAction.TYPING)
    await asyncio.sleep(1)

    # Get user stats for personalized greeting
    stats = await memory_manager.get_user_stats(user.id)

    # Keyboard buttons for commands
    keyboard = [
        [KeyboardButton("/createquiz"), KeyboardButton("/myquizzes")],
        [KeyboardButton("/startquiz"), KeyboardButton("/stats")],
        [KeyboardButton("/history"), KeyboardButton("/leaderboard")],
        [KeyboardButton("/help"), KeyboardButton("/reset")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    # Personalized greeting based on history
    if stats and stats.get('quizzes_taken', 0) > 0:
        greeting = (f"👋 Welcome back, *{user.first_name}*!\n\n"
                   f"📊 Your Stats:\n"
                   f"• Total Score: {stats.get('total_score', 0)}\n"
                   f"• Quizzes Taken: {stats.get('quizzes_taken', 0)}\n"
                   f"• Best Score: {stats.get('best_score', 0)}\n\n"
                   f"Ready for another quiz? 🎯")
    else:
        greeting = (f"👋 Hello, *{user.first_name}*! Welcome to the Quiz Bot! 🤖\n\n"
                   f"This bot now remembers your progress and stats!\n\n"
                   f"Use the commands below to create and manage your quizzes.")

    await context.bot.send_message(
        chat_id=user.id,
        text=greeting,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


# ==================== Stats Command ====================
async def stats(update: Update, context: CallbackContext):
    """Display user statistics"""
    user = update.message.from_user

    # Check cache first
    cached_stats = cache.get_stats(user.id)
    if cached_stats:
        stats_data = cached_stats
    else:
        stats_data = await memory_manager.get_user_stats(user.id)
        cache.set_stats(user.id, stats_data)

    if not stats_data:
        await update.message.reply_text(
            "📊 No statistics available yet. Take a quiz to get started!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    message = (
        f"📊 *Your Quiz Statistics*\n\n"
        f"👤 Username: {stats_data.get('username', 'N/A')}\n"
        f"🆔 User ID: {stats_data.get('user_id', 'N/A')}\n\n"
        f"*Performance:*\n"
        f"• Total Score: {stats_data.get('total_score', 0)} points\n"
        f"• Quizzes Taken: {stats_data.get('quizzes_taken', 0)}\n"
        f"• Average Score: {stats_data.get('average_score', 0)}\n"
        f"• Best Score: {stats_data.get('best_score', 0)}\n"
        f"• Total Correct: {stats_data.get('total_correct', 0)}\n"
        f"• Total Answered: {stats_data.get('total_answered', 0)}\n\n"
        f"📅 Member since: {stats_data.get('join_date', 'N/A')}\n"
        f"🕐 Last active: {stats_data.get('last_active', 'N/A')}"
    )

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


# ==================== History Command ====================
async def history(update: Update, context: CallbackContext):
    """Show user's quiz history"""
    user = update.message.from_user

    sessions = await memory_manager.get_user_history(user.id, limit=10)

    if not sessions:
        await update.message.reply_text(
            "📜 No quiz history found. Start taking quizzes to build your history!",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    message = "*📜 Your Recent Quiz History*\n\n"

    for idx, session in enumerate(sessions, 1):
        status_emoji = "✅" if session.get('status') == 'completed' else "⏸️"
        score = session.get('score', 0)
        correct = session.get('correct_answers', 0)
        total = session.get('total_questions', 0)

        message += (
            f"{idx}. {status_emoji} *{session.get('quiz_name', 'Unknown')}*\n"
            f"   Score: {score} | Correct: {correct}/{total}\n"
            f"   Date: {session.get('start_time', 'N/A')}\n\n"
        )

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


# ==================== Leaderboard Command ====================
async def leaderboard(update: Update, context: CallbackContext):
    """Show global leaderboard"""
    # Check cache first
    cached_leaderboard = cache.get_leaderboard()
    if cached_leaderboard:
        leaders = cached_leaderboard
    else:
        leaders = await memory_manager.get_leaderboard(limit=10)
        cache.set_leaderboard(leaders)

    if not leaders:
        await update.message.reply_text(
            "🏆 No leaderboard data available yet.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    message = "*🏆 Global Leaderboard - Top 10*\n\n"

    for idx, leader in enumerate(leaders, 1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        username = leader.get('username') or leader.get('first_name', 'Anonymous')
        score = leader.get('total_score', 0)
        quizzes = leader.get('quizzes_taken', 0)

        message += f"{medal} *{username}*\n   Score: {score} | Quizzes: {quizzes}\n\n"

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


# ==================== Reset Command ====================
async def reset(update: Update, context: CallbackContext):
    """Reset user data (GDPR compliance)"""
    user = update.message.from_user

    # Confirmation keyboard
    keyboard = [
        [InlineKeyboardButton("✅ Yes, delete my data", callback_data='confirm_reset')],
        [InlineKeyboardButton("❌ Cancel", callback_data='cancel_reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ *Warning*\n\n"
        "This will permanently delete all your data including:\n"
        "• Quiz history\n"
        "• Statistics\n"
        "• Preferences\n"
        "• Achievements\n\n"
        "Are you sure you want to continue?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def handle_reset_callback(update: Update, context: CallbackContext):
    """Handle reset confirmation"""
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if query.data == 'confirm_reset':
        # Delete user data
        await memory_manager.delete_user_data(user.id)
        cache.delete_user(user.id)
        cache.invalidate_stats(user.id)

        await query.edit_message_text(
            "✅ *Data Deleted*\n\n"
            "All your data has been permanently deleted.\n"
            "You can start fresh with /start",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(
            "❌ Reset cancelled. Your data is safe.",
            parse_mode=ParseMode.MARKDOWN
        )


# ==================== Help Command ====================
async def help_command(update: Update, context: CallbackContext):
    """Show help message"""
    help_text = (
        "*📚 Quiz Bot Commands*\n\n"
        "*Quiz Management:*\n"
        "/createquiz - Create a new quiz\n"
        "/myquizzes - View your created quizzes\n"
        "/startquiz <name> - Start a quiz\n"
        "/deletequiz - Delete a quiz\n\n"
        "*Statistics & History:*\n"
        "/stats - View your statistics\n"
        "/history - View quiz history\n"
        "/leaderboard - Global leaderboard\n\n"
        "*Settings:*\n"
        "/reset - Delete all your data\n"
        "/help - Show this message\n\n"
        "🤖 This bot now remembers your progress!"
    )

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


# ==================== Export Data Command (Admin/User) ====================
async def export_data(update: Update, context: CallbackContext):
    """Export user data (GDPR compliance)"""
    user = update.message.from_user

    await update.message.reply_text("📦 Exporting your data... Please wait.")

    export_path = backup_manager.export_user_data(user.id)

    if export_path:
        # Send the JSON file to the user
        with open(export_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=user.id,
                document=f,
                filename=f"my_quiz_data_{user.id}.json",
                caption="📦 Here's all your data in JSON format."
            )
    else:
        await update.message.reply_text(
            "❌ Failed to export data. Please try again later."
        )


# ==================== Continue with original quiz functions ====================
# (Include all the original quiz creation and management functions here)
# For brevity, I'll add the key ones that need memory integration

async def finalize_quiz(update: Update, context: CallbackContext):
    """Finalize the quiz and save it with metadata"""
    user_id = context.user_data['creator']
    quiz_name = context.user_data['quiz_name']
    questions = context.user_data['questions']
    time_gap = context.user_data.get('time_gap', 0)

    # Save to quizzes dict
    quizzes[quiz_name] = {
        'creator': user_id,
        'questions': questions,
        'status': 'ready',
        'time_gap': time_gap
    }

    # Save quiz metadata to database
    await memory_manager.save_quiz_metadata(
        quiz_name=quiz_name,
        creator_id=user_id,
        total_questions=len(questions),
        time_gap=time_gap
    )

    await update.message.reply_text(
        f"🚀 Quiz '{quiz_name}' created successfully!\n"
        f"Use /startquiz {quiz_name} to start it.",
        parse_mode=ParseMode.MARKDOWN
    )

    return ConversationHandler.END


# ==================== Main Function ====================
def main():
    """Run the bot"""
    application = Application.builder().token(bot_token).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("export", export_data))

    # Add callback handlers
    application.add_handler(CallbackQueryHandler(
        handle_reset_callback,
        pattern='^(confirm_reset|cancel_reset)$'
    ))

    # Start automatic backups
    backup_scheduler = AutoBackupScheduler(backup_manager, interval_hours=24)
    asyncio.create_task(backup_scheduler.start())

    logger.info("Quiz Bot with Memory started!")

    # Run the bot
    application.run_polling()


if __name__ == '__main__':
    main()
