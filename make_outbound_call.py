#!/usr/bin/env python3
"""
Simple Outbound Call Trigger Script

Run this script to make an outbound call to a specified phone number.
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def make_outbound_call(target_phone):
    """Create dispatch and initiate outbound call"""
    print(f"📞 Making outbound call to {target_phone}...")
    
    # Validate phone number format
    if not target_phone.startswith('+'):
        target_phone = f"+{target_phone}"
    
    # Get trunk ID (you may need to update this)
    trunk_id = os.getenv("OUTBOUND_TRUNK_ID")  # Set this in your .env file
    if not trunk_id:
        # Try to read from saved file
        if os.path.exists('trunk_id.txt'):
            with open('trunk_id.txt', 'r') as f:
                trunk_id = f.read().strip()
    
    if not trunk_id:
        print("❌ No outbound trunk ID found. Run setup_outbound_calls.py first")
        return False
    
    # Create room name with timestamp
    room_name = f"outbound-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Prepare metadata
    metadata = {
        'phone_number': target_phone,
        'trunk_id': trunk_id,
        'call_type': 'outbound',
        'timestamp': datetime.now().isoformat()
    }
    
    try:
        # Create dispatch command
        cmd = [
            'lk', 'dispatch', 'create',
            '--new-room',
            '--room', room_name,
            '--agent-name', 'restaurant-outbound-agent',
            '--metadata', json.dumps(metadata)
        ]
        
        print(f"🚀 Creating dispatch...")
        print(f"   Room: {room_name}")
        print(f"   Target: {target_phone}")
        print(f"   Trunk: {trunk_id}")
        
        # Execute the dispatch command
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if result.returncode == 0:
            print("✅ Dispatch created successfully!")
            print("📞 Your phone should start ringing in 5-10 seconds...")
            print("📱 Answer the call to speak with the AI agent!")
            print("\nCall details:")
            print(f"   Room: {room_name}")
            print(f"   Phone: {target_phone}")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to create dispatch")
            print("Error:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error making outbound call: {e}")
        return False


def main():
    """Main function"""
    print("📞 Restaurant Voice Agent - Outbound Call")
    print("="*45)
    
    # Check if phone number provided
    if len(sys.argv) < 2:
        print("Usage: python make_outbound_call.py <phone_number>")
        print("Example: python make_outbound_call.py +1234567890")
        print("Example: python make_outbound_call.py 1234567890")
        sys.exit(1)
    
    target_phone = sys.argv[1]
    
    # Validate environment
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please check your .env file")
        sys.exit(1)
    
    print(f"🎯 Target phone number: {target_phone}")
    
    # Make the call
    success = make_outbound_call(target_phone)
    
    if success:
        print("\n✅ Outbound call initiated!")
        print("📱 Answer your phone to speak with the AI agent")
        print("\nThe agent will:")
        print("   • Identify itself and the restaurant")
        print("   • Ask if it's a good time to talk")
        print("   • Handle reservations and inquiries")
        print("   • Provide restaurant information")
    else:
        print("\n❌ Failed to initiate outbound call")
        print("Please check:")
        print("   • LiveKit CLI is installed and working")
        print("   • Environment variables are set correctly")
        print("   • Outbound trunk is configured")
        print("   • Agent is running (python outbound_agent.py dev)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Call cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 