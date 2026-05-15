#!/usr/bin/env python3
"""
Generate secure secrets for CIRS deployment
Run: python generate_secrets.py
"""
import secrets

def generate_secret(length=32):
    """Generate a cryptographically secure random string"""
    return secrets.token_urlsafe(length)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🔐 CIRS Deployment Secret Generator")
    print("="*50 + "\n")
    
    jwt_secret = generate_secret(32)
    db_password = generate_secret(20)
    
    print("📌 Generated Secrets - Copy these to Render Dashboard:\n")
    print(f"JWT_SECRET:\n  {jwt_secret}\n")
    print(f"DB_PASSWORD (if creating new user):\n  {db_password}\n")
    
    print("="*50)
    print("⚠️  Keep these secrets safe - don't commit to GitHub!")
    print("="*50 + "\n")
