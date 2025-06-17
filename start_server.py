#!/usr/bin/env python3
"""
Restaurant Voice Agent Startup Script

This script helps initialize the database with sample data and starts the FastAPI server.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import uvicorn

from database import db

load_dotenv()


async def setup_database():
    """Initialize database with sample data"""
    print("🔧 Setting up database...")
    
    try:
        # Test database connection
        restaurant = await db.get_restaurant()
        
        if not restaurant:
            print("❌ No restaurant found. Please insert restaurant data manually:")
            print("""
                Run this SQL in your Supabase SQL Editor:

                INSERT INTO restaurants (name, address, phone, email, opening_hours, max_capacity) VALUES (
                    'Bella Vista Restaurant',
                    '123 Gourmet Street, Culinary District, NY 10001',
                    '+1-555-BELLA-01',
                    'reservations@bellavista.com',
                    '{
                        "monday": {"open": "17:00", "close": "22:00"},
                        "tuesday": {"open": "17:00", "close": "22:00"},
                        "wednesday": {"open": "17:00", "close": "22:00"},
                        "thursday": {"open": "17:00", "close": "22:00"},
                        "friday": {"open": "17:00", "close": "23:00"},
                        "saturday": {"open": "17:00", "close": "23:00"},
                        "sunday": {"open": "17:00", "close": "21:00"}
                    }',
                    50
                );
            """)
            return False
        
        print(f"✅ Restaurant found: {restaurant.name}")
        
        # Check if menu exists
        menu_items = await db.get_menu()
        if not menu_items:
            print("📋 No menu found. Seeding sample menu...")
            success = await db.seed_sample_menu()
            if success:
                print("✅ Sample menu seeded successfully")
            else:
                print("❌ Failed to seed menu")
                return False
        else:
            print(f"✅ Menu found with {len(menu_items)} items")
        
        print("✅ Database setup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        "GOOGLE_API_KEY",
        "SUPABASE_URL", 
        "SUPABASE_ANON_KEY"
    ]
    
    optional_vars = [
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY", 
        "LIVEKIT_API_SECRET",
        "MANAGER_PHONE"
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
        else:
            print(f"✅ {var} is set")
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
        else:
            print(f"✅ {var} is set")
    
    if missing_required:
        print(f"❌ Missing required environment variables: {', '.join(missing_required)}")
        print("Please add them to your .env file")
        return False
    
    if missing_optional:
        print(f"⚠️  Missing optional environment variables: {', '.join(missing_optional)}")
        print("These are needed for full functionality")
    
    return True


def start_fastapi_server():
    """Start the FastAPI server"""
    print("🚀 Starting FastAPI server...")
    print("Server will be available at: http://localhost:8000")
    print("API docs will be available at: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


async def main():
    """Main startup function"""
    print("🎭 Restaurant Voice Agent Server Startup")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    # Setup database
    db_ready = await setup_database()
    if not db_ready:
        print("\n❌ Database setup failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ All checks passed! Starting server...")
    print("\nAvailable endpoints:")
    print("  📋 GET  /health - Health check")
    print("  🏢 GET  /restaurant/info - Restaurant information")
    print("  📞 POST /agent/start-call - Start agent call")
    print("  📅 POST /bookings - Create booking")
    print("  🔍 POST /bookings/check-availability - Check availability")
    print("  🍽️  POST /menu/search - Search menu")
    print("  📝 POST /special-requests - Handle special requests")
    print("  📊 GET  /analytics/calls - Call analytics")
    print("\n" + "=" * 50)
    
    # Start the server
    start_fastapi_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1) 