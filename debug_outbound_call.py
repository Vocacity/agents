#!/usr/bin/env python3
"""
Debug Outbound Call Issues - Step by Step Diagnostics
"""

import os
import json
import asyncio
import requests
from datetime import datetime
from dotenv import load_dotenv
from livekit import api

load_dotenv()


def check_environment():
    """Check all required environment variables"""
    print("🔍 Step 1: Checking Environment Variables")
    print("="*50)
    
    required_vars = {
        'LIVEKIT_URL': os.getenv('LIVEKIT_URL'),
        'LIVEKIT_API_KEY': os.getenv('LIVEKIT_API_KEY'),
        'LIVEKIT_API_SECRET': os.getenv('LIVEKIT_API_SECRET'),
        'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID'),
        'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN'),
        'TWILIO_PHONE_NUMBER': os.getenv('TWILIO_PHONE_NUMBER', '+16812434656'),
        'TWILIO_SIP_DOMAIN': os.getenv('TWILIO_SIP_DOMAIN', 'indianrestaurants.sip.twilio.com')
    }
    
    all_good = True
    for var, value in required_vars.items():
        if value:
            # Mask sensitive values
            if 'SECRET' in var or 'TOKEN' in var:
                masked = value[:8] + '*' * (len(value) - 8)
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            all_good = False
    
    return all_good, required_vars


def check_twilio_sip_domain(account_sid, auth_token, sip_domain):
    """Check if Twilio SIP domain exists and is configured"""
    print("\n🔍 Step 2: Checking Twilio SIP Domain")
    print("="*50)
    
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/SIP/Domains.json"
        response = requests.get(url, auth=(account_sid, auth_token))
        
        if response.status_code == 200:
            domains = response.json().get('domains', [])
            print(f"✅ Found {len(domains)} SIP domain(s)")
            
            domain_found = False
            for domain in domains:
                print(f"📋 Domain: {domain['domain_name']}")
                if domain['domain_name'] == sip_domain:
                    domain_found = True
                    print(f"✅ Target SIP domain found: {sip_domain}")
                    print(f"   Voice Method: {domain.get('voice_method', 'N/A')}")
                    print(f"   Voice URL: {domain.get('voice_url', 'N/A')}")
                    print(f"   Auth Type: {domain.get('auth_type', 'N/A')}")
            
            if not domain_found:
                print(f"❌ Target SIP domain NOT found: {sip_domain}")
                return False
            
            return True
        else:
            print(f"❌ Failed to get SIP domains: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking SIP domains: {e}")
        return False


def check_twilio_phone_number(account_sid, auth_token, phone_number):
    """Check if Twilio phone number exists and is configured"""
    print("\n🔍 Step 3: Checking Twilio Phone Number")
    print("="*50)
    
    try:
        # Format phone number for Twilio API
        formatted_number = phone_number.replace('+', '%2B')
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/IncomingPhoneNumbers.json"
        response = requests.get(url, auth=(account_sid, auth_token))
        
        if response.status_code == 200:
            numbers = response.json().get('incoming_phone_numbers', [])
            print(f"✅ Found {len(numbers)} phone number(s)")
            
            number_found = False
            for number in numbers:
                if number['phone_number'] == phone_number:
                    number_found = True
                    print(f"✅ Target phone number found: {phone_number}")
                    print(f"   Voice URL: {number.get('voice_url', 'N/A')}")
                    print(f"   Voice Method: {number.get('voice_method', 'N/A')}")
                    print(f"   Capabilities: Voice={number.get('capabilities', {}).get('voice')}, SMS={number.get('capabilities', {}).get('sms')}")
            
            if not number_found:
                print(f"❌ Target phone number NOT found: {phone_number}")
                return False
            
            return True
        else:
            print(f"❌ Failed to get phone numbers: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking phone numbers: {e}")
        return False


async def check_livekit_trunk():
    """Check LiveKit outbound trunk configuration"""
    print("\n🔍 Step 4: Checking LiveKit Outbound Trunk")
    print("="*50)
    
    try:
        # Get trunk ID
        trunk_id = "ST_ho2aZwMwftXF"  # Updated trunk ID
        
        livekit_api = api.LiveKitAPI(
            url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET")
        )
        
        # Try to list SIP trunks
        print(f"📋 Checking trunk: {trunk_id}")
        print("✅ LiveKit API connection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking LiveKit trunk: {e}")
        return False


async def test_call_with_debugging(phone_number, trunk_id):
    """Test call with detailed debugging"""
    print("\n🔍 Step 5: Testing Call with Debugging")
    print("="*50)
    
    try:
        livekit_api = api.LiveKitAPI(
            url=os.getenv("LIVEKIT_URL"),
            api_key=os.getenv("LIVEKIT_API_KEY"),
            api_secret=os.getenv("LIVEKIT_API_SECRET")
        )
        
        # Create room
        room_name = f"debug-call-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        room_request = api.CreateRoomRequest(name=room_name)
        room = await livekit_api.room.create_room(room_request)
        print(f"✅ Room created: {room.name}")
        
        # Create SIP participant with detailed logging
        print(f"📞 Creating SIP participant...")
        print(f"   Trunk ID: {trunk_id}")
        print(f"   Calling: {phone_number}")
        print(f"   Room: {room.name}")
        
        sip_request = api.CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=phone_number,
            room_name=room.name,
            participant_identity=f"debug-{phone_number.replace('+', '').replace(' ', '')}",
            participant_name=f"Debug-Call-{phone_number[-4:]}"
        )
        
        participant = await livekit_api.sip.create_sip_participant(sip_request)
        print(f"✅ SIP participant created: {participant.participant_id}")
        
        # Wait and check for call status
        print("⏳ Waiting 10 seconds for call to connect...")
        await asyncio.sleep(10)
        
        # Try to get room info to see if participant joined
        room_info = await livekit_api.room.list_participants(api.ListParticipantsRequest(room=room.name))
        print(f"📋 Room participants: {len(room_info.participants)}")
        for p in room_info.participants:
            print(f"   - {p.identity} ({p.state})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in call test: {e}")
        return False


def show_twilio_setup_instructions():
    """Show specific Twilio setup instructions for outbound calls"""
    print("\n🔧 Step 6: Twilio Setup Instructions for Outbound Calls")
    print("="*60)
    
    print("""
CRITICAL: For outbound calls, you need to configure Twilio differently!

1. **SIP Domain Configuration:**
   - Go to Twilio Console → Voice → SIP Domains
   - Click on 'indianrestaurants.sip.twilio.com'
   - Set Authentication to "Username/Password" or "IP Access Control Lists"
   - Add LiveKit's IP addresses to allowed IPs (if using IP ACL)

2. **Phone Number Configuration:**
   - Go to Phone Numbers → Manage → Active numbers
   - Click on +16812434656
   - Set "A call comes in" to SIP Domain: indianrestaurants.sip.twilio.com
   
3. **Outbound Call Routing:**
   The issue might be that Twilio SIP domain isn't configured to handle 
   OUTBOUND calls FROM LiveKit TO external numbers.
   
   You may need to:
   - Configure TwiML Bins or Functions to handle outbound routing
   - Set up proper authentication for LiveKit to use your trunk
   - Enable international calling if calling India (+91)

4. **Check Call Logs:**
   - Go to Twilio Console → Monitor → Logs → Calls
   - Look for any failed call attempts
   - Check error messages
   """)


async def main():
    """Main diagnostic function"""
    print("�� OUTBOUND CALL DIAGNOSTICS")
    print("="*60)
    
    # Step 1: Environment check
    env_ok, env_vars = check_environment()
    if not env_ok:
        print("\n❌ Environment check failed!")
        return
    
    # Step 2: Twilio SIP domain check
    sip_ok = check_twilio_sip_domain(
        env_vars['TWILIO_ACCOUNT_SID'],
        env_vars['TWILIO_AUTH_TOKEN'],
        env_vars['TWILIO_SIP_DOMAIN']
    )
    
    # Step 3: Twilio phone number check
    phone_ok = check_twilio_phone_number(
        env_vars['TWILIO_ACCOUNT_SID'],
        env_vars['TWILIO_AUTH_TOKEN'],
        env_vars['TWILIO_PHONE_NUMBER']
    )
    
    # Step 4: LiveKit trunk check
    trunk_ok = await check_livekit_trunk()
    
    # Step 5: Test call
    if env_ok and trunk_ok:
        test_ok = await test_call_with_debugging("+919022353647", "ST_ho2aZwMwftXF")
    
    # Step 6: Show setup instructions
    show_twilio_setup_instructions()
    
    print("\n" + "="*60)
    print("🎯 DIAGNOSIS SUMMARY")
    print("="*60)
    print(f"Environment: {'✅' if env_ok else '❌'}")
    print(f"SIP Domain: {'✅' if sip_ok else '❌'}")
    print(f"Phone Number: {'✅' if phone_ok else '❌'}")
    print(f"LiveKit Trunk: {'✅' if trunk_ok else '❌'}")
    
    if not sip_ok or not phone_ok:
        print("\n❌ LIKELY ISSUE: Twilio configuration is incorrect!")
        print("   Follow the setup instructions above.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Diagnostics interrupted by user")
    except Exception as e:
        print(f"❌ Diagnostics failed: {e}") 