#!/usr/bin/env python3
"""
Test script to debug restore password issues
"""
import sys
import os
sys.path.insert(0, '.')

# Enable verbose logging
os.environ['VERBOSE'] = 'true'

try:
    from main import DatabaseBackupApp
    import logging
    
    # Set up detailed logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Initialize the app
    print("🔧 Initializing backup application...")
    app = DatabaseBackupApp('config.yaml')
    app.load_databases_from_config()
    app.load_services_from_config()
    
    # Get the controller
    controller_id = 'immich_new'
    backup_file = './backups/backup_immich_2025-10-31-02-26-22.tar.gz'
    
    print(f"\n📋 Restore Configuration:")
    print(f"  Controller ID: {controller_id}")
    print(f"  Backup file: {backup_file}")
    print(f"  File exists: {os.path.exists(backup_file)}")
    
    controller = app.backup_manager.controllers[controller_id]
    print(f"  Target host: {controller.db_config.host}")
    print(f"  Target database: {controller.db_config.database}")
    print(f"  Username: {controller.db_config.username}")
    
    # Test .pgpass file creation
    print(f"\n🔐 Testing .pgpass file creation...")
    pgpass_path = controller._create_pgpass_file()
    if pgpass_path:
        print(f"✅ .pgpass file created: {pgpass_path}")
        
        # Verify the file content format
        with open(pgpass_path, 'r') as f:
            content = f.read().strip()
            parts = content.split(':')
            if len(parts) == 5:
                print(f"✅ .pgpass format correct: {parts[0]}:{parts[1]}:{parts[2]}:{parts[3]}:***")
            else:
                print(f"❌ .pgpass format incorrect: {len(parts)} parts")
        
        # Test environment variable setting
        import subprocess
        env = os.environ.copy()
        env['PGPASSFILE'] = pgpass_path
        env['PGHOST'] = controller.db_config.host
        env['PGPORT'] = str(controller.db_config.port)
        env['PGUSER'] = controller.db_config.username
        env['PGDATABASE'] = controller.db_config.database
        
        print(f"\n🧪 Testing direct psql connection...")
        test_cmd = ["psql", "--command", "SELECT 1;"]
        
        try:
            result = subprocess.run(test_cmd, env=env, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Direct psql connection successful")
            else:
                print(f"❌ Direct psql connection failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("❌ Direct psql connection timed out")
        except Exception as e:
            print(f"❌ Direct psql connection error: {e}")
        
        # Clean up
        controller._cleanup_pgpass_file()
        print("🧹 Cleaned up .pgpass file")
    else:
        print("❌ Failed to create .pgpass file")
    
    print(f"\n🔄 Now attempting restore...")
    success = app.restore_database(backup_file, controller_id)
    
    if success:
        print("✅ Restore completed successfully!")
    else:
        print("❌ Restore failed!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()