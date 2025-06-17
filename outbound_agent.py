#!/usr/bin/env python3
"""
Outbound Calling Agent for Restaurant Voice Agent

This agent handles outbound calls and automatically dials specified phone numbers.
"""

import asyncio
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from livekit import agents, api, rtc
from livekit.agents import AgentSession, Agent, RoomInputOptions, JobContext
from livekit.agents.llm import function_tool
from livekit.plugins import google

from database import db
from schema import CallStatus, BookingStatus

load_dotenv()


class OutboundRestaurantAgent(Agent):
    def __init__(self) -> None:
        instructions = """You are a professional restaurant voice agent making an outbound call. 

Your role is to:
- Make courtesy calls to customers about their reservations
- Follow up on previous inquiries or bookings
- Conduct customer satisfaction surveys  
- Provide special offers and promotions
- Handle reservation confirmations or changes

Guidelines for outbound calls:
- Always identify yourself and the restaurant first
- Be polite and ask if it's a good time to talk
- Clearly state the purpose of your call
- Keep the call focused and respectful of their time
- Offer to call back if it's not convenient
- Handle any questions about reservations or the restaurant
- Thank them for their time before ending the call

Example opening:
"Hello, this is [Agent Name] calling from [Restaurant Name]. I'm calling to follow up on your recent reservation inquiry. Is this a good time to talk?"

Be warm, professional, and efficient. Respect if they want to end the call."""

        super().__init__(instructions=instructions)
        self.current_call_log_id: Optional[int] = None
        self.target_phone: Optional[str] = None
        self.call_purpose: str = "follow_up"

    async def start_outbound_call_tracking(self, phone_number: str, purpose: str = "outbound_call"):
        """Start tracking an outbound call"""
        try:
            self.target_phone = phone_number
            self.call_purpose = purpose
            call_log = await db.create_call_log(
                phone_number=phone_number,
                status=CallStatus.OUTGOING,
                purpose=purpose
            )
            self.current_call_log_id = call_log.id
            print(f"📞 Started outbound call tracking: {call_log.id}")
        except Exception as e:
            print(f"Error starting outbound call tracking: {e}")

    async def end_outbound_call_tracking(self, transcript: Optional[str] = None, notes: Optional[str] = None):
        """End outbound call tracking"""
        if self.current_call_log_id:
            try:
                await db.update_call_log(
                    self.current_call_log_id,
                    call_end=datetime.now().isoformat(),
                    status=CallStatus.COMPLETED.value,
                    transcript=transcript,
                    agent_notes=notes
                )
                print(f"📞 Ended outbound call tracking: {self.current_call_log_id}")
            except Exception as e:
                print(f"Error ending outbound call tracking: {e}")

    @function_tool
    async def create_booking_tool(self, customer_name: str, phone_number: str, booking_date: str, 
                                 booking_time: str, party_size: int, special_requests: str = None):
        """Create a new booking for the customer"""
        try:
            booking = await db.create_booking(
                customer_name=customer_name,
                phone_number=phone_number,
                booking_date=booking_date,
                booking_time=booking_time,
                party_size=party_size,
                special_requests=special_requests,
                status=BookingStatus.CONFIRMED
            )
            
            return f"Perfect! I've created your reservation for {party_size} people on {booking_date} at {booking_time}. Your confirmation code is {booking.confirmation_code}. We look forward to seeing you!"
            
        except Exception as e:
            return f"I apologize, but I encountered an error creating your booking: {str(e)}. Let me transfer you to our reservations team."

    @function_tool
    async def check_availability_tool(self, booking_date: str, booking_time: str, party_size: int):
        """Check availability for a specific date and time"""
        try:
            is_available = await db.check_availability(booking_date, booking_time, party_size)
            
            if is_available:
                return f"Great news! We have availability for {party_size} people on {booking_date} at {booking_time}. Would you like me to make this reservation for you?"
            else:
                # Suggest alternative times
                alternatives = await db.get_alternative_times(booking_date, party_size)
                if alternatives:
                    alt_times = ", ".join([alt['time'] for alt in alternatives[:3]])
                    return f"I don't have availability at {booking_time}, but I can offer you these times on {booking_date}: {alt_times}. Would any of these work for you?"
                else:
                    return f"Unfortunately, we're fully booked on {booking_date}. Would you like me to check another date?"
                    
        except Exception as e:
            return f"I'm having trouble checking availability right now. Let me connect you with our reservations team."

    @function_tool
    async def find_booking_tool(self, confirmation_code: str):
        """Find existing booking by confirmation code"""
        try:
            booking = await db.get_booking_by_confirmation(confirmation_code)
            if booking:
                return f"I found your reservation: {booking.customer_name} for {booking.party_size} people on {booking.booking_date} at {booking.booking_time}. How can I help you with this reservation?"
            else:
                return f"I couldn't find a reservation with confirmation code {confirmation_code}. Could you please verify the code or provide your phone number?"
        except Exception as e:
            return f"I'm having trouble accessing our reservation system. Let me connect you with our reservations team."

    @function_tool
    async def get_restaurant_info_tool(self, info_type: str):
        """Get restaurant information"""
        try:
            restaurant = await db.get_restaurant()
            if not restaurant:
                return "I'm sorry, I don't have the restaurant information available right now."
            
            if info_type.lower() in ['hours', 'time', 'open']:
                hours_info = []
                for day, hours in restaurant.opening_hours.items():
                    if 'closed' in hours:
                        hours_info.append(f"{day.capitalize()}: Closed")
                    else:
                        hours_info.append(f"{day.capitalize()}: {hours['open']} - {hours['close']}")
                return f"Our hours are: {', '.join(hours_info)}"
                
            elif info_type.lower() in ['location', 'address', 'where']:
                return f"We're located at {restaurant.address}. You can reach us at {restaurant.phone}."
                
            elif info_type.lower() in ['contact', 'phone', 'email']:
                return f"You can contact us at {restaurant.phone} or email us at {restaurant.email}."
                
            else:
                return f"We're {restaurant.name}, located at {restaurant.address}. We're open {restaurant.opening_hours}. You can reach us at {restaurant.phone}."
                
        except Exception as e:
            return "I'm having trouble accessing our restaurant information right now."


async def entrypoint(ctx: JobContext):
    """Entry point for outbound calling agent"""
    print(f"🤖 Outbound agent starting for room: {ctx.room.name}")
    
    # Parse metadata for call information
    metadata = {}
    
    # Check room metadata first
    if ctx.room.metadata:
        try:
            metadata = json.loads(ctx.room.metadata)
            print(f"📋 Room metadata: {metadata}")
        except Exception as e:
            print(f"❌ Error parsing room metadata: {e}")
            print(f"📋 Raw room metadata: {ctx.room.metadata}")
    
    # Also check if there's metadata in the job context
    if hasattr(ctx, 'metadata') and ctx.metadata:
        try:
            job_metadata = json.loads(ctx.metadata)
            print(f"📋 Job metadata: {job_metadata}")
            metadata.update(job_metadata)  # Merge job metadata
        except Exception as e:
            print(f"❌ Error parsing job metadata: {e}")
    
    # Check for metadata in environment or other sources
    if not metadata:
        print("⚠️  No metadata found, checking environment variables...")
        # Fallback to environment variables for testing
        target_phone = os.getenv('TEST_PHONE_NUMBER', 'unknown')
        trunk_id = os.getenv('OUTBOUND_TRUNK_ID')
        if target_phone != 'unknown':
            metadata = {
                'phone_number': target_phone,
                'trunk_id': trunk_id,
                'call_type': 'outbound_test'
            }
            print(f"📋 Using fallback metadata: {metadata}")
    
    target_phone = metadata.get('phone_number', 'unknown')
    trunk_id = metadata.get('trunk_id')
    call_purpose = metadata.get('call_type', 'outbound_call')
    
    print(f"📞 Target phone: {target_phone}")
    print(f"📡 Trunk ID: {trunk_id}")
    
    # Create session with outbound-specific instructions
    session = AgentSession(
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",
            voice="Puck",
            temperature=0.6,
            instructions=f"""You are making an outbound call to {target_phone} for our restaurant. 

Your goal is to:
1. Identify yourself and the restaurant professionally
2. Ask if it's a good time to talk
3. State the purpose of your call clearly
4. Handle any restaurant-related questions or requests
5. Be respectful of their time

Available tools:
- create_booking_tool(customer_name, phone_number, booking_date, booking_time, party_size, special_requests)
- check_availability_tool(booking_date, booking_time, party_size)
- find_booking_tool(confirmation_code) 
- get_restaurant_info_tool(info_type)

Keep the conversation focused and professional. If they're not interested or it's a bad time, politely offer to call back later and end the call gracefully."""
        )
    )

    # Create outbound agent
    agent = OutboundRestaurantAgent()
    
    # Start call tracking
    await agent.start_outbound_call_tracking(target_phone, call_purpose)

    # Connect to room first
    await ctx.connect()
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=agent,
    )

    # Tools are now automatically registered via @function_tool decorator
    # No need to manually register them

    # Wait a moment for room to be ready
    await asyncio.sleep(2)
    
    # Create SIP participant to dial the target number
    if target_phone != 'unknown' and trunk_id:
        print(f"📞 Dialing {target_phone}...")
        
        try:
            # Get LiveKit API client
            livekit_api = api.LiveKitAPI(
                url=os.getenv("LIVEKIT_URL"),
                api_key=os.getenv("LIVEKIT_API_KEY"),
                api_secret=os.getenv("LIVEKIT_API_SECRET")
            )
            
            # Create SIP participant request
            sip_request = api.CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=target_phone,
                room_name=ctx.room.name,
                participant_identity=f"sip-{target_phone.replace('+', '').replace(' ', '')}",
                participant_name=f"Customer-{target_phone[-4:]}"
            )
            
            # Create the SIP participant (this initiates the call)
            participant = await livekit_api.sip.create_sip_participant(sip_request)
            print(f"✅ SIP participant created: {participant.participant_id}")
            print(f"📞 Calling {target_phone}...")
            
            # Wait for participant to join and call to be answered
            await asyncio.sleep(5)
            
            # Start conversation once call is answered
            await session.generate_reply(
                instructions=f"The outbound call to {target_phone} should now be connected. Start the conversation with a professional greeting, identify yourself and the restaurant, and ask if it's a good time to talk."
            )
            
        except Exception as e:
            print(f"❌ Error creating SIP participant: {e}")
            # Still continue the session in case manual testing
    else:
        print("⚠️  No phone number or trunk ID provided, waiting for manual connection")
        await session.generate_reply(
            instructions="You are ready to handle an outbound call. Wait for the customer to join and then greet them professionally."
        )


if __name__ == "__main__":
    # Agent name for explicit dispatch (required for outbound calls)
    agents.cli.run_app(agents.WorkerOptions(
        entrypoint_fnc=entrypoint,
        agent_name="restaurant-outbound-agent"  # Must match dispatch command
    )) 