"""
Admin User Setup Script
Run this to create your admin account with custom credentials
"""
import os
import sys
import secrets
import string
from getpass import getpass
from app import create_app
from models import db, User, Subscription, Organization
from datetime import datetime, timedelta


def generate_secure_password(length=20):
    """Generate cryptographically secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_+="
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def create_admin():
    """Create admin user with interactive setup"""
    app = create_app()

    print("=" * 70)
    print("🛡️  RECON PLATFORM - ADMIN USER SETUP")
    print("=" * 70)
    print()

    # Interactive mode or CLI args
    if len(sys.argv) >= 3:
        username = sys.argv[1]
        password = sys.argv[2]
        email = sys.argv[3] if len(sys.argv) > 3 else f"{username}@recon.kryzensys.com"
        full_name = sys.argv[4] if len(sys.argv) > 4 else "Platform Administrator"
    else:
        print("Choose setup mode:")
        print("  [1] Interactive (you type username/password)")
        print("  [2] Auto-generate secure credentials")
        print("  [3] Quick admin (admin/admin123) - DEV ONLY")
        print()
        mode = input("Select mode [1/2/3]: ").strip()

        if mode == "2":
            username = "admin"
            password = generate_secure_password(24)
            email = "admin@recon.kryzensys.com"
            full_name = "Platform Administrator"
            print(f"\n✅ Auto-generated secure password: {password}\n")
        elif mode == "3":
            username = "admin"
            password = "Admin@2026!Secure"
            email = "admin@recon.kryzensys.com"
            full_name = "Platform Administrator"
            print(f"\n⚠️  DEV credentials: admin / {password}\n")
        else:
            print()
            username = input("Admin username: ").strip()
            email = input("Admin email: ").strip()
            full_name = input("Full name (optional): ").strip() or "Platform Administrator"
            password = getpass("Admin password (min 12 chars): ").strip()
            confirm = getpass("Confirm password: ").strip()

            if password != confirm:
                print("❌ Passwords don't match!")
                sys.exit(1)
            if len(password) < 12:
                print("❌ Password must be at least 12 characters!")
                sys.exit(1)

    with app.app_context():
        # Check if admin already exists
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing:
            print(f"⚠️  User '{existing.username}' already exists!")
            print(f"   Email: {existing.email}")
            print(f"   Is admin: {existing.is_admin}")
            print()
            response = input("Update password? [y/N]: ").strip().lower()
            if response == "y":
                existing.set_password(password)
                existing.is_admin = True
                existing.is_verified = True
                existing.role = "superadmin"
                existing.plan = "enterprise"
                existing.is_active = True
                existing.is_banned = False
                db.session.commit()
                print("✅ Admin password updated!")
            else:
                print("❌ Cancelled")
                sys.exit(0)
            admin = existing
        else:
            # Create new admin user
            admin = User(
                username=username,
                email=email,
                full_name=full_name,
                role="superadmin",
                plan="enterprise",
                is_admin=True,
                is_verified=True,
                is_active=True,
                is_banned=False,
                email_verified_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                timezone="UTC",
                locale="en",
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.flush()  # Get admin.id

            # Create subscription
            sub = Subscription(
                user_id=admin.id,
                plan="enterprise",
                status="active",
                started_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=3650),  # 10 years
                payment_provider="system",
                external_id="admin-bootstrap",
                amount=0,
            )
            db.session.add(sub)

            # Create or assign to organization
            org = Organization.query.filter_by(slug="kryzensys").first()
            if not org:
                org = Organization(
                    name="KRYZENSYS",
                    slug="kryzensys",
                    plan="enterprise",
                    billing_email=email,
                    max_seats=999,
                    is_active=True,
                    created_at=datetime.utcnow(),
                )
                db.session.add(org)
                db.session.flush()

            admin.organization_id = org.id
            db.session.commit()
            print("✅ Admin user created successfully!")

        # Print summary
        print()
        print("=" * 70)
        print("🎉  ADMIN CREDENTIALS")
        print("=" * 70)
        print(f"  Username:  {admin.username}")
        print(f"  Email:     {admin.email}")
        print(f"  Password:  {password}")
        print(f"  Role:      {admin.role}")
        print(f"  Plan:      {admin.plan}")
        print(f"  User ID:   {admin.id}")
        print(f"  Status:    {'Active' if admin.is_active else 'Inactive'}")
        print("=" * 70)
        print()
        print("🔐 Save these credentials in a secure password manager!")
        print("🌐 Login at: /admin/login")
        print("📧 Or via API: POST /api/v1/auth/login")
        print()

        # Save to file (encrypted with restrictive permissions)
        creds_file = "/root/recon_admin_credentials.txt"
        try:
            with open(creds_file, "w") as f:
                f.write(f"RECON PLATFORM - ADMIN CREDENTIALS\n")
                f.write(f"Generated: {datetime.utcnow().isoformat()}\n")
                f.write(f"{'='*60}\n")
                f.write(f"Username: {admin.username}\n")
                f.write(f"Email:    {admin.email}\n")
                f.write(f"Password: {password}\n")
                f.write(f"User ID:  {admin.id}\n")
                f.write(f"Role:     {admin.role}\n")
                f.write(f"{'='*60}\n")
            os.chmod(creds_file, 0o600)  # Owner read/write only
            print(f"📁 Credentials also saved to: {creds_file}")
            print("   (file mode 600 - only root can read)")
        except Exception as e:
            print(f"⚠️  Could not save to file: {e}")


if __name__ == "__main__":
    create_admin()
