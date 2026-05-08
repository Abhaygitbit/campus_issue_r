#!/usr/bin/env python3
"""
Database migration script to add missing columns
Run this before starting the app if you get schema errors
"""
import os
import sys

from app import app, db, run_migrations

print("=" * 60)
print("Campus Issue Resolver - Database Migration")
print("=" * 60)

with app.app_context():
    try:
        print("\n✓ Creating tables...")
        db.create_all()
        
        print("✓ Running migrations...")
        run_migrations()
        
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nYou can now start the app with: python app.py")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
