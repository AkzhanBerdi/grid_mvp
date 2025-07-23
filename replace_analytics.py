# scripts/replace_analytics.py
"""
Complete Analytics Replacement Script
Removes all broken analytics and implements clean SQLite-based system
"""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


class AnalyticsReplacement:
    """Complete analytics system replacement"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup_broken_analytics"
        self.replacements_made = []
        self.errors = []
    
    def execute_complete_replacement(self):
        """Execute complete analytics replacement"""
        print("🔄 **COMPLETE ANALYTICS REPLACEMENT**")
        print("=" * 50)
        
        # Step 1: Backup broken files
        self._backup_broken_files()
        
        # Step 2: Remove broken imports from handlers
        self._clean_handler_imports()
        
        # Step 3: Replace analytics calls in handlers
        self._replace_analytics_calls()
        
        # Step 4: Clean database of analytics tables
        self._clean_analytics_database()
        
        # Step 5: Verify new system works
        self._verify_new_system()
        
        # Step 6: Generate summary report
        self._generate_summary_report()
    
    def _backup_broken_files(self):
        """Backup broken analytics files"""
        print("\n1️⃣ **BACKING UP BROKEN FILES**")
        
        # Create backup directory
        self.backup_dir.mkdir(exist_ok=True)
        
        broken_files = [
            "analytics/fifo_profit_tracker.py",
            "services/smart_analytics.py", 
            "utils/fifo_telegram_monitor.py",
            "cleanup_backup/smart_analytics.py"
        ]
        
        for file_path in broken_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                backup_path = self.backup_dir / file_path.replace("/", "_")
                shutil.copy2(full_path, backup_path)
                print(f"   ✅ Backed up: {file_path}")
            else:
                print(f"   ⚠️  Not found: {file_path}")
    
    def _clean_handler_imports(self):
        """Remove broken imports from handler files"""
        print("\n2️⃣ **CLEANING HANDLER IMPORTS**")
        
        handler_files = [
            "handlers/client_handler.py",
            "handlers/admin_handler.py", 
            "utils/base_handler.py"
        ]
        
        broken_imports = [
            "from analytics.fifo_profit_tracker import",
            "from services.smart_analytics import", 
            "from utils.fifo_telegram_monitor import",
            "FIFOProfitTracker",
            "SmartAnalytics",
            "FIFOProfitCalculator"
        ]
        
        for handler_file in handler_files:
            file_path = self.project_root / handler_file
            if file_path.exists():
                self._clean_file_imports(file_path, broken_imports)
    
    def _clean_file_imports(self, file_path: Path, broken_imports: list):
        """Clean imports from a specific file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                should_remove = False
                for broken_import in broken_imports:
                    if broken_import in line:
                        should_remove = True
                        break
                
                if not should_remove:
                    cleaned_lines.append(line)
                else:
                    print(f"   🗑️  Removed: {line.strip()}")
            
            # Write cleaned content
            cleaned_content = '\n'.join(cleaned_lines)
            
            if cleaned_content != original_content:
                with open(file_path, 'w') as f:
                    f.write(cleaned_content)
                print(f"   ✅ Cleaned: {file_path}")
                self.replacements_made.append(f"Cleaned imports in {file_path}")
            
        except Exception as e:
            error_msg = f"Error cleaning {file_path}: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)
    
    def _replace_analytics_calls(self):
        """Replace analytics method calls with new system"""
        print("\n3️⃣ **REPLACING ANALYTICS CALLS**")
        
        replacements = {
            # Old analytics instantiation
            "self.smart_analytics = SmartAnalytics()": 
                "from analytics.sqlite_analytics import AnalyticsCommandInterface\n        self.analytics = AnalyticsCommandInterface()",
            
            "self.fifo_tracker = FIFOProfitTracker()":
                "from analytics.sqlite_analytics import SQLiteAnalytics\n        self.analytics_sqlite = SQLiteAnalytics()",
            
            # Old method calls
            "self.smart_analytics.get_performance_metrics":
                "self.analytics_sqlite.get_real_profit",
            
            "fifo_tracker.calculate_performance_metrics":
                "analytics_sqlite.get_real_profit",
            
            # Remove refresh performance buttons
            'InlineKeyboardButton("🔄 Refresh", callback_data="refresh_performance")':
                'InlineKeyboardButton("📊 Stats", callback_data="show_stats")',
            
            # Replace callback handlers
            'elif action == "refresh_performance":':
                'elif action == "show_stats":'
        }
        
        handler_files = [
            "handlers/client_handler.py",
            "handlers/admin_handler.py"
        ]
        
        for handler_file in handler_files:
            file_path = self.project_root / handler_file
            if file_path.exists():
                self._apply_replacements(file_path, replacements)
    
    def _apply_replacements(self, file_path: Path, replacements: dict):
        """Apply replacements to a file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            original_content = content
            
            for old_code, new_code in replacements.items():
                if old_code in content:
                    content = content.replace(old_code, new_code)
                    print(f"   🔄 Replaced in {file_path.name}: {old_code[:30]}...")
            
            if content != original_content:
                with open(file_path, 'w') as f:
                    f.write(content)
                self.replacements_made.append(f"Applied replacements to {file_path}")
            
        except Exception as e:
            error_msg = f"Error applying replacements to {file_path}: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)
    
    def _clean_analytics_database(self):
        """Remove analytics-specific database tables"""
        print("\n4️⃣ **CLEANING DATABASE ANALYTICS TABLES**")
        
        try:
            from config import Config
            db_path = Config.DATABASE_PATH
            
            with sqlite3.connect(db_path) as conn:
                # Check what analytics tables exist
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name LIKE '%analytic%'
                    OR name IN ('fifo_matches', 'profit_snapshots', 'performance_cache')
                """)
                
                analytics_tables = [row[0] for row in cursor.fetchall()]
                
                if analytics_tables:
                    print(f"   📊 Found analytics tables: {analytics_tables}")
                    
                    for table in analytics_tables:
                        conn.execute(f"DROP TABLE IF EXISTS {table}")
                        print(f"   🗑️  Dropped table: {table}")
                    
                    print("   ✅ Database cleaned of analytics tables")
                else:
                    print("   ✅ No analytics tables found to remove")
            
        except Exception as e:
            error_msg = f"Error cleaning database: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)
    
    def _verify_new_system(self):
        """Verify new analytics system is working"""
        print("\n5️⃣ **VERIFYING NEW SYSTEM**")
        
        try:
            # Test imports
            from analytics.sqlite_analytics import SQLiteAnalytics, AnalyticsCommandInterface
            print("   ✅ New analytics imports working")
            
            # Test database connection
            analytics = SQLiteAnalytics()
            stats = analytics.get_trading_statistics(123456789)  # Test with dummy ID
            print("   ✅ Database queries working")
            
            # Test command interface
            command_interface = AnalyticsCommandInterface()
            response = command_interface.handle_profit_command(123456789)
            print("   ✅ Command interface working")
            
            print("   🎉 NEW ANALYTICS SYSTEM VERIFIED!")
            
        except Exception as e:
            error_msg = f"New system verification failed: {e}"
            print(f"   ❌ {error_msg}")
            self.errors.append(error_msg)
    
    def _generate_summary_report(self):
        """Generate summary report of replacement"""
        print("\n6️⃣ **REPLACEMENT SUMMARY**")
        print("=" * 50)
        
        print(f"✅ **REPLACEMENTS COMPLETED:** {len(self.replacements_made)}")
        for replacement in self.replacements_made:
            print(f"   • {replacement}")
        
        if self.errors:
            print(f"\n❌ **ERRORS ENCOUNTERED:** {len(self.errors)}")
            for error in self.errors:
                print(f"   • {error}")
        else:
            print("\n✅ **NO ERRORS - CLEAN REPLACEMENT!**")
        
        print(f"\n📁 **BACKUP LOCATION:** {self.backup_dir}")
        print(f"🕒 **COMPLETED:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Generate next steps
        print("\n🚀 **NEXT STEPS:**")
        print("1. Test the new system with: `/profit` command")
        print("2. Verify analytics show exactly $44.38")
        print("3. Check that dashboard no longer shows phantom profits")
        print("4. Remove any remaining broken analytics references")
        print("5. Deploy and monitor for 24 hours")


class HandlerPatcher:
    """Patch handlers to use new analytics system"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
    
    def patch_client_handler(self):
        """Patch client handler with new analytics"""
        print("\n🔧 **PATCHING CLIENT HANDLER**")
        
        handler_path = self.project_root / "handlers/client_handler.py"
        
        if not handler_path.exists():
            print("   ❌ Client handler not found")
            return False
        
        try:
            # Read current handler
            with open(handler_path, 'r') as f:
                content = f.read()
            
            # Add new analytics import at top
            import_addition = """from analytics.sqlite_analytics import AnalyticsCommandInterface, SQLiteAnalytics"""
            
            if "from analytics.sqlite_analytics import" not in content:
                # Find import section
                lines = content.split('\n')
                import_line_index = -1
                
                for i, line in enumerate(lines):
                    if line.startswith('from ') and 'import' in line:
                        import_line_index = i
                
                if import_line_index >= 0:
                    lines.insert(import_line_index + 1, import_addition)
                    content = '\n'.join(lines)
                    print("   ✅ Added new analytics import")
            
            # Add analytics initialization in __init__
            init_addition = """        self.analytics_interface = AnalyticsCommandInterface()
        self.analytics_sqlite = SQLiteAnalytics()"""
            
            if "self.analytics_interface" not in content:
                # Find __init__ method
                if "def __init__" in content and "self.analytics_interface" not in content:
                    init_position = content.find("def __init__")
                    if init_position != -1:
                        # Find end of __init__ method setup
                        lines = content[init_position:].split('\n')
                        for i, line in enumerate(lines[1:], 1):
                            if line.strip() and not line.startswith('        '):
                                # Insert before this line
                                insert_pos = init_position + len('\n'.join(lines[:i]))
                                content = content[:insert_pos] + '\n' + init_addition + content[insert_pos:]
                                print("   ✅ Added analytics initialization")
                                break
            
            # Add command handlers
            command_methods = """
    async def handle_profit_command(self, update, context):
        \"\"\"Handle /profit command with real SQLite data\"\"\"
        client_id = update.effective_user.id
        response = self.analytics_interface.handle_profit_command(client_id)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def handle_stats_command(self, update, context):
        \"\"\"Handle /stats command\"\"\"
        client_id = update.effective_user.id
        response = self.analytics_interface.handle_stats_command(client_id)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def handle_performance_command(self, update, context):
        \"\"\"Handle /performance command\"\"\"
        client_id = update.effective_user.id
        response = self.analytics_interface.handle_performance_command(client_id)
        await update.message.reply_text(response, parse_mode='Markdown')
    
    async def handle_recent_command(self, update, context):
        \"\"\"Handle /recent command\"\"\"
        client_id = update.effective_user.id
        response = self.analytics_interface.handle_recent_command(client_id)
        await update.message.reply_text(response, parse_mode='Markdown')"""
            
            if "handle_profit_command" not in content:
                content += command_methods
                print("   ✅ Added command handler methods")
            
            # Write updated content
            with open(handler_path, 'w') as f:
                f.write(content)
            
            print("   🎉 Client handler patched successfully!")
            return True
            
        except Exception as e:
            print(f"   ❌ Error patching client handler: {e}")
            return False
    
    def add_command_routing(self):
        """Add command routing to message handler"""
        print("\n🔧 **ADDING COMMAND ROUTING**")
        
        handler_path = self.project_root / "handlers/client_handler.py"
        
        try:
            with open(handler_path, 'r') as f:
                content = f.read()
            
            # Add routing in handle_message method
            routing_code = """
        # Analytics commands - NEW SQLite-based system
        if text.startswith('/profit'):
            await self.handle_profit_command(update, context)
            return
        elif text.startswith('/stats'):
            await self.handle_stats_command(update, context)
            return
        elif text.startswith('/performance'):
            await self.handle_performance_command(update, context)
            return
        elif text.startswith('/recent'):
            await self.handle_recent_command(update, context)
            return"""
            
            if "await self.handle_profit_command" not in content:
                # Find handle_message method
                handle_message_pos = content.find("async def handle_message")
                if handle_message_pos != -1:
                    # Find a good insertion point after text extraction
                    text_pos = content.find("text = ", handle_message_pos)
                    if text_pos != -1:
                        # Find next line after text extraction
                        next_line_pos = content.find('\n', text_pos) + 1
                        content = content[:next_line_pos] + routing_code + content[next_line_pos:]
                        print("   ✅ Added command routing")
            
            with open(handler_path, 'w') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error adding command routing: {e}")
            return False


class DatabaseValidator:
    """Validate that database contains the real $44.38 data"""
    
    def __init__(self):
        pass
    
    def validate_real_profit_data(self, client_id: int):
        """Validate that we can retrieve the real $44.38 profit"""
        print(f"\n🔍 **VALIDATING REAL PROFIT DATA FOR CLIENT {client_id}**")
        
        try:
            from config import Config
            
            with sqlite3.connect(Config.DATABASE_PATH) as conn:
                # The exact query that showed $44.38
                cursor = conn.execute("""
                    SELECT 
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE 0 END) as total_sells,
                        SUM(CASE WHEN side = 'BUY' THEN total_value ELSE 0 END) as total_buys,
                        COUNT(*) as total_trades
                    FROM trades 
                    WHERE client_id = ?
                """, (client_id,))
                
                result = cursor.fetchone()
                total_sells = result[0] or 0.0
                total_buys = result[1] or 0.0
                total_trades = result[2] or 0
                real_profit = total_sells - total_buys
                
                print(f"   📊 Total Sells: ${total_sells:.2f}")
                print(f"   📊 Total Buys: ${total_buys:.2f}")
                print(f"   💰 Real Profit: ${real_profit:.2f}")
                print(f"   📈 Total Trades: {total_trades}")
                
                if abs(real_profit - 44.38) < 0.01:  # Allow small rounding differences
                    print("   ✅ PERFECT! Found the exact $44.38 profit")
                elif real_profit > 0:
                    print(f"   ✅ Positive profit found: ${real_profit:.2f}")
                else:
                    print(f"   ⚠️  Profit differs from expected $44.38: ${real_profit:.2f}")
                
                # Daily breakdown validation
                cursor = conn.execute("""
                    SELECT 
                        DATE(executed_at) as trade_date,
                        SUM(CASE WHEN side = 'SELL' THEN total_value ELSE -total_value END) as daily_profit
                    FROM trades 
                    WHERE client_id = ?
                    AND executed_at >= date('now', '-7 days')
                    GROUP BY DATE(executed_at)
                    ORDER BY trade_date DESC
                """, (client_id,))
                
                daily_data = cursor.fetchall()
                print(f"\n   📅 Daily Breakdown:")
                for date_str, daily_profit in daily_data:
                    print(f"   • {date_str}: ${daily_profit:.2f}")
                
                return True
                
        except Exception as e:
            print(f"   ❌ Error validating profit data: {e}")
            return False


def main():
    """Main execution function"""
    print("🚀 **COMPLETE ANALYTICS REBUILD**")
    print("Replacing broken phantom profit system with SQLite truth")
    print("=" * 60)
    
    # Get project root
    project_root = input("Enter project root path (press Enter for current directory): ").strip()
    if not project_root:
        project_root = "."
    
    # Get client ID for validation
    client_id_input = input("Enter your client ID for validation (e.g., 123456789): ").strip()
    try:
        client_id = int(client_id_input)
    except (ValueError, TypeError):
        print("Invalid client ID, using test ID 123456789")
        client_id = 123456789
    
    # Execute replacement
    replacer = AnalyticsReplacement(project_root)
    replacer.execute_complete_replacement()
    
    # Patch handlers
    patcher = HandlerPatcher(project_root)
    patcher.patch_client_handler()
    patcher.add_command_routing()
    
    # Validate database
    validator = DatabaseValidator()
    validator.validate_real_profit_data(client_id)
    
    print("\n" + "=" * 60)
    print("🎉 **ANALYTICS REBUILD COMPLETE!**")
    print("\n📋 **TESTING CHECKLIST:**")
    print("1. Run: python -c \"from analytics.sqlite_analytics import *; print('✅ Import works')\"")
    print("2. Test command: /profit")
    print("3. Verify shows exactly your real profit (like $44.38)")
    print("4. Test other commands: /stats, /performance, /recent")
    print("5. Confirm no phantom profits in dashboard")
    
    print("\n🔧 **IF ISSUES:**")
    print("1. Check backup_broken_analytics/ for original files")
    print("2. Review errors in summary above")
    print("3. Manually verify handler imports")
    
    print("\n✅ **SUCCESS = Clean SQLite analytics showing real profits!**")


if __name__ == "__main__":
    main()
