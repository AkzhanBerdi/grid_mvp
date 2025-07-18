#!/usr/bin/env python3
"""
GridTrader Pro Codebase Cleanup Script
Removes unused code and simplifies the project structure
Based on analysis of 'phase-1-deployed' commit
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict
import logging

class CodebaseCleanup:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "cleanup_backup"
        self.removed_files = []
        self.removed_dirs = []
        self.logger = self._setup_logging()
        
    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def create_backup(self):
        """Create backup before cleanup"""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        self.backup_dir.mkdir(exist_ok=True)
        self.logger.info(f"📦 Creating backup in {self.backup_dir}")
        
        # Copy critical files to backup
        backup_files = self._get_files_to_backup()
        for file_path in backup_files:
            if file_path.exists():
                backup_path = self.backup_dir / file_path.name
                shutil.copy2(file_path, backup_path)
                
        self.logger.info(f"✅ Backup created with {len(backup_files)} files")

    def _get_files_to_backup(self) -> List[Path]:
        """Get list of files to backup before removal"""
        return [
            self.project_root / "final_fixed_test_runner.py",
            self.project_root / "quick_test_runner.py", 
            self.project_root / "integration" / "fifo_integration.py",
            self.project_root / "services" / "enhanced_dual_scale_manager.py",
            self.project_root / "services" / "smart_analytics.py",
            self.project_root / "utils" / "crypto.py",  # Keep main functions, remove debug
        ]

    def remove_test_and_debug_files(self):
        """Remove test runners and debug files"""
        test_files = [
            "final_fixed_test_runner.py",
            "quick_test_runner.py", 
            "run_production_tests.sh",
            "test_production_suite.py",
            "minimal_test.py",
            "debug_test_failures.py",
        ]
        
        self.logger.info("🧹 Removing test and debug files...")
        
        for filename in test_files:
            file_path = self.project_root / filename
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(filename)
                self.logger.info(f"  ❌ Removed: {filename}")

    def remove_integration_experiments(self):
        """Remove integration and experimental code"""
        integration_dir = self.project_root / "integration"
        if integration_dir.exists():
            shutil.rmtree(integration_dir)
            self.removed_dirs.append("integration/")
            self.logger.info("  ❌ Removed: integration/ directory")

    def remove_unused_services(self):
        """Remove services that are no longer used"""
        unused_services = [
            "services/enhanced_dual_scale_manager.py",  # Replaced by single_advanced_grid_manager
            "services/dual_scale_grid_manager.py",      # Legacy dual grid system
            "services/smart_analytics.py",              # Debug analytics, not used in production
        ]
        
        self.logger.info("🧹 Removing unused services...")
        
        for service_path in unused_services:
            file_path = self.project_root / service_path
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(service_path)
                self.logger.info(f"  ❌ Removed: {service_path}")

    def clean_crypto_utils(self):
        """Clean up crypto.py - remove debug functions but keep core functionality"""
        crypto_file = self.project_root / "utils" / "crypto.py"
        
        if not crypto_file.exists():
            return
            
        self.logger.info("🧹 Cleaning crypto.py debug functions...")
        
        with open(crypto_file, 'r') as f:
            content = f.read()
        
        # Remove debug_client_encryption function and main execution
        lines = content.split('\n')
        cleaned_lines = []
        skip_mode = False
        
        for line in lines:
            # Start skipping at debug function
            if 'def debug_client_encryption(' in line:
                skip_mode = True
                continue
            
            # Stop skipping at next function or class
            if skip_mode and (line.startswith('def ') or line.startswith('class ') or line.startswith('if __name__')):
                if line.startswith('if __name__'):
                    break  # Remove everything after this
                skip_mode = False
            
            if not skip_mode:
                cleaned_lines.append(line)
        
        # Write cleaned content
        with open(crypto_file, 'w') as f:
            f.write('\n'.join(cleaned_lines))
        
        self.logger.info("  ✅ Cleaned crypto.py debug functions")

    def remove_docker_and_deployment_files(self):
        """Remove Docker and deployment files (keep only if needed)"""
        deployment_files = [
            ".dockerignore",
            "Dockerfile", 
            "docker-compose.yml",
            "run_production_tests.sh",
        ]
        
        self.logger.info("🧹 Removing deployment files (can be recreated if needed)...")
        
        for filename in deployment_files:
            file_path = self.project_root / filename
            if file_path.exists():
                file_path.unlink()
                self.removed_files.append(filename)
                self.logger.info(f"  ❌ Removed: {filename}")

    def clean_gitignore(self):
        """Clean up .gitignore - remove entries for deleted files"""
        gitignore_file = self.project_root / ".gitignore"
        
        if not gitignore_file.exists():
            return
            
        self.logger.info("🧹 Cleaning .gitignore...")
        
        with open(gitignore_file, 'r') as f:
            lines = f.readlines()
        
        # Remove specific debug file patterns
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            
            # Skip lines that reference removed files
            if any(pattern in line for pattern in [
                'debug_test_failures.py',
                'minimal_test.py', 
                'fix_*.py',
                'immediate_fix.sh',
                '*_test.py',
                'test_logs/',
            ]):
                continue
            
            cleaned_lines.append(line + '\n' if not line.endswith('\n') else line)
        
        with open(gitignore_file, 'w') as f:
            f.writelines(cleaned_lines)
        
        self.logger.info("  ✅ Cleaned .gitignore")

    def remove_unused_imports_from_main(self):
        """Clean up unused imports in main.py"""
        main_file = self.project_root / "main.py"
        
        if not main_file.exists():
            return
            
        self.logger.info("🧹 Cleaning unused imports in main.py...")
        
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Remove commented-out imports and debug imports
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip commented import lines
            if line.strip().startswith('# from ') or line.strip().startswith('#from '):
                continue
            
            # Skip debug-related imports
            if any(debug_term in line for debug_term in [
                'debug_', 'test_', 'final_fixed_', 'quick_test_'
            ]):
                continue
                
            cleaned_lines.append(line)
        
        with open(main_file, 'w') as f:
            f.write('\n'.join(cleaned_lines))
        
        self.logger.info("  ✅ Cleaned main.py imports")

    def create_essential_files_summary(self):
        """Create summary of essential files that remain"""
        essential_structure = {
            "Core Application": [
                "main.py",
                "config.py",
            ],
            "Handlers": [
                "handlers/client_handler.py",
            ],
            "Services": [
                "services/grid_orchestrator.py",
                "services/single_advanced_grid_manager.py",
                "services/advanced_trading_features.py",
                "services/fifo_service.py",
                "services/telegram_notifier.py",
            ],
            "Repositories": [
                "repositories/client_repository.py", 
                "repositories/trade_repository.py",
            ],
            "Models": [
                "models/client.py",
            ],
            "Database": [
                "database/db_setup.py",
            ],
            "Utils": [
                "utils/base_handler.py",
                "utils/crypto.py",
                "utils/network_utils.py",
                "utils/network_recovery.py",
                "utils/fifo_telegram_monitor.py",
            ],
        }
        
        summary_file = self.project_root / "ESSENTIAL_FILES.md"
        
        with open(summary_file, 'w') as f:
            f.write("# GridTrader Pro - Essential Files\n\n")
            f.write("After cleanup, these are the core files for production:\n\n")
            
            for category, files in essential_structure.items():
                f.write(f"## {category}\n")
                for file_path in files:
                    if (self.project_root / file_path).exists():
                        f.write(f"- ✅ {file_path}\n")
                    else:
                        f.write(f"- ❌ {file_path} (missing)\n")
                f.write("\n")
            
            f.write("## Removed Files\n")
            for removed_file in self.removed_files:
                f.write(f"- ❌ {removed_file}\n")
            
            if self.removed_dirs:
                f.write("\n## Removed Directories\n")
                for removed_dir in self.removed_dirs:
                    f.write(f"- ❌ {removed_dir}\n")
        
        self.logger.info(f"📋 Created essential files summary: ESSENTIAL_FILES.md")

    def run_cleanup(self, create_backup: bool = True):
        """Run the complete cleanup process"""
        self.logger.info("🚀 Starting GridTrader Pro codebase cleanup...")
        
        if create_backup:
            self.create_backup()
        
        # Run cleanup steps
        self.remove_test_and_debug_files()
        self.remove_integration_experiments() 
        self.remove_unused_services()
        self.clean_crypto_utils()
        self.remove_docker_and_deployment_files()
        self.clean_gitignore()
        self.remove_unused_imports_from_main()
        
        # Create documentation
        self.create_essential_files_summary()
        
        # Final summary
        self.logger.info("✅ Cleanup completed!")
        self.logger.info(f"📁 Removed {len(self.removed_files)} files")
        self.logger.info(f"📁 Removed {len(self.removed_dirs)} directories")
        
        if create_backup:
            self.logger.info(f"💾 Backup available in: {self.backup_dir}")
        
        self.logger.info("🎯 Your codebase is now simplified and production-ready!")
        
        return {
            "removed_files": self.removed_files,
            "removed_dirs": self.removed_dirs,
            "backup_location": str(self.backup_dir) if create_backup else None
        }

def main():
    """Command line interface for cleanup"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up GridTrader Pro codebase")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be removed without actually removing")
    parser.add_argument("--project-dir", default=".", help="Project directory path")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - Showing what would be removed:")
        print()
        print("FILES TO REMOVE:")
        files_to_remove = [
            "final_fixed_test_runner.py",
            "quick_test_runner.py",
            "run_production_tests.sh", 
            "services/enhanced_dual_scale_manager.py",
            "services/dual_scale_grid_manager.py",
            "services/smart_analytics.py",
            ".dockerignore",
            "Dockerfile",
        ]
        for f in files_to_remove:
            print(f"  - {f}")
        
        print()
        print("DIRECTORIES TO REMOVE:")
        print("  - integration/")
        
        print()
        print("FILES TO CLEAN:")
        print("  - utils/crypto.py (remove debug functions)")
        print("  - .gitignore (remove debug patterns)")
        print("  - main.py (remove unused imports)")
        
        print()
        print("Run without --dry-run to execute cleanup")
        return
    
    # Run actual cleanup
    cleanup = CodebaseCleanup(args.project_dir)
    result = cleanup.run_cleanup(create_backup=not args.no_backup)
    
    print()
    print("🎉 CLEANUP COMPLETE!")
    print(f"📊 Summary: {len(result['removed_files'])} files and {len(result['removed_dirs'])} directories removed")
    
    if result['backup_location']:
        print(f"💾 Backup saved to: {result['backup_location']}")
    
    print("📋 Check ESSENTIAL_FILES.md for remaining file structure")

if __name__ == "__main__":
    main()
