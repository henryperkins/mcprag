#!/usr/bin/env python3
"""
Local cleanup script for MCP RAG system.
Removes only local files and temporary data, keeps Azure resources.
"""
import os
import shutil
from pathlib import Path

def cleanup_local_files():
    """Clean up local files and directories."""
    print("🧹 Cleaning up local files...")
    
    # Files to remove
    files_to_remove = [
        '.env',
        'app.db',
        '*.log',
        '*.tmp'
    ]
    
    # Directories to remove
    directories_to_remove = [
        '__pycache__',
        '.pytest_cache',
        'logs',
        'temp',
        '.mypy_cache',
        'htmlcov',
        '.coverage'
    ]
    
    removed_count = 0
    
    # Remove specific files
    for file_pattern in files_to_remove:
        if '*' in file_pattern:
            # Handle wildcards
            import glob
            for file_path in glob.glob(file_pattern):
                try:
                    os.remove(file_path)
                    print(f"   ✅ Removed: {file_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Could not remove {file_path}: {e}")
        else:
            path = Path(file_pattern)
            if path.exists() and path.is_file():
                try:
                    path.unlink()
                    print(f"   ✅ Removed file: {file_pattern}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Could not remove {file_pattern}: {e}")
    
    # Remove directories
    for dir_name in directories_to_remove:
        path = Path(dir_name)
        if path.exists() and path.is_dir():
            try:
                shutil.rmtree(path)
                print(f"   ✅ Removed directory: {dir_name}")
                removed_count += 1
            except Exception as e:
                print(f"   ⚠️  Could not remove {dir_name}: {e}")
    
    # Clean up Python cache recursively
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs[:]:  # Use slice to modify list during iteration
            if dir_name == '__pycache__':
                cache_path = Path(root) / dir_name
                try:
                    shutil.rmtree(cache_path)
                    print(f"   ✅ Removed cache: {cache_path}")
                    removed_count += 1
                    dirs.remove(dir_name)  # Don't recurse into removed directory
                except Exception as e:
                    print(f"   ⚠️  Could not remove {cache_path}: {e}")
    
    if removed_count == 0:
        print("   ℹ️  No files found to clean up")
    else:
        print(f"   ✅ Cleaned up {removed_count} items")

def reset_example_repo():
    """Reset the example repository to clean state."""
    print("🔄 Resetting example repository...")
    
    example_repo = Path('example-repo')
    if example_repo.exists():
        # Keep the example files but remove any generated content
        generated_files = [
            'example-repo/*.pyc',
            'example-repo/__pycache__'
        ]
        
        removed = 0
        for pattern in generated_files:
            if '*' in pattern:
                import glob
                for file_path in glob.glob(pattern):
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        print(f"   ✅ Cleaned: {file_path}")
                        removed += 1
                    except Exception as e:
                        print(f"   ⚠️  Could not clean {file_path}: {e}")
        
        if removed == 0:
            print("   ℹ️  Example repository already clean")
        else:
            print(f"   ✅ Cleaned {removed} items from example repository")
    else:
        print("   ℹ️  No example repository found")

def backup_env_file():
    """Create a backup of .env file before deletion."""
    env_file = Path('.env')
    if env_file.exists():
        backup_file = Path('.env.backup')
        try:
            shutil.copy2(env_file, backup_file)
            print(f"   💾 Created backup: .env.backup")
            return True
        except Exception as e:
            print(f"   ⚠️  Could not create backup: {e}")
            return False
    return False

def main():
    """Main cleanup function."""
    print("🧹 MCP RAG Local Cleanup")
    print("=" * 30)
    print("This script will clean up:")
    print("• Temporary files and caches")
    print("• Environment configuration (.env)")
    print("• Python cache directories")
    print("• Log files")
    print("\n✅ Azure resources will NOT be affected")
    
    # Confirmation
    confirm = input("\nProceed with local cleanup? (y/N): ").lower().strip()
    if confirm not in ['y', 'yes']:
        print("❌ Cleanup cancelled.")
        return
    
    # Backup .env file
    print("\n💾 Creating backup of configuration...")
    backup_created = backup_env_file()
    
    # Clean up files
    print("\n🧹 Cleaning up local files...")
    cleanup_local_files()
    
    # Reset example repo
    print("\n🔄 Cleaning example repository...")
    reset_example_repo()
    
    print("\n🎉 Local cleanup completed!")
    print("\n📋 Summary:")
    print("✅ Temporary files removed")
    print("✅ Python caches cleared")
    if backup_created:
        print("✅ Configuration backed up to .env.backup")
    print("✅ Example repository cleaned")
    print("\n💡 To restore configuration:")
    print("   cp .env.backup .env")
    print("\n🔗 Azure resources remain active:")
    print("   https://portal.azure.com")

if __name__ == "__main__":
    main()
