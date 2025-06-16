import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional, List
from dotenv import load_dotenv

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import google

from database import db
from schema import CallStatus, BookingStatus

load_dotenv()


class RestaurantAssistant(Agent):
    def __init__(self) -> None:
        instructions = """You are a friendly and professional restaurant voice assistant for taking reservations and helping customers. 

Your capabilities include:
- Taking new restaurant reservations
- Checking availability for specific dates and times
- Modifying or canceling existing bookings
- Providing information about the restaurant (hours, location, menu, ambience)
- Answering questions about dietary restrictions and allergies
- Helping with special requests and seat preferences
- Routing complex requests to management when needed

Guidelines:
- Always be polite, warm, and professional
- Ask for necessary information step by step (date, time, party size, name, phone number)
- Confirm all booking details before finalizing
- Provide confirmation codes for new bookings
- If a time is not available, suggest alternative times
- For cancellations, ask for confirmation code or phone number
- For special seating requests, offer to connect with manager
- Keep responses concise but helpful

Example interaction flow:
1. Greet the customer warmly
2. Ask how you can help them today
3. For reservations: collect date, time, party size, name, phone number
4. Check availability and confirm or suggest alternatives
5. Handle any special requests or menu questions
6. Finalize booking and provide confirmation code
7. Summarize the reservation details"""

        super().__init__(instructions=instructions)
        self.current_call_log_id: Optional[int] = None
        self.customer_phone: Optional[str] = None

    async def start_call_tracking(self, phone_number: str):
        """Start tracking a new call"""
        try:
            self.customer_phone = phone_number
            call_log = await db.create_call_log(
                phone_number=phone_number,
                status=CallStatus.ANSWERED,
                purpose="reservation_inquiry"
            )
            self.current_call_log_id = call_log.id
        except Exception as e:
            print(f"Error starting call tracking: {e}")

    async def end_call_tracking(self, transcript: Optional[str] = None, notes: Optional[str] = None):
        """End call tracking and update call log"""
        if self.current_call_log_id:
            try:
                await db.update_call_log(
                    self.current_call_log_id,
                    call_end=datetime.now().isoformat(),
                    status=CallStatus.COMPLETED.value,
                    transcript=transcript,
                    agent_notes=notes
                )
            except Exception as e:
                print(f"Error ending call tracking: {e}")

    async def create_booking_tool(self, customer_name: str, phone_number: str, 
                                 booking_date: str, booking_time: str, party_size: int,
                                 special_requests: Optional[str] = None) -> str:
        """Tool function to create a restaurant booking"""
        try:
            # Parse date and time
            booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
            
            # Get or create customer
            customer_response = await db.get_or_create_customer(phone_number, customer_name)
            if not customer_response.success:
                return f"Error: {customer_response.message}"
            
            # Create booking
            booking_response = await db.create_booking(
                customer_id=customer_response.customer.id,
                booking_date=booking_datetime,
                party_size=party_size,
                special_requests=special_requests
            )
            
            if booking_response.success:
                return f"Booking confirmed! Your confirmation code is {booking_response.confirmation_code}. " \
                       f"We have you down for {party_size} people on {booking_date} at {booking_time}. " \
                       f"We look forward to seeing you!"
            else:
                return f"Sorry, {booking_response.message}"
                
        except ValueError as e:
            return "Please provide the date in YYYY-MM-DD format and time in HH:MM format (24-hour)."
        except Exception as e:
            return f"I'm sorry, there was an error processing your booking: {str(e)}"

    async def check_availability_tool(self, booking_date: str, booking_time: str, party_size: int) -> str:
        """Tool function to check restaurant availability"""
        try:
            booking_datetime = datetime.strptime(f"{booking_date} {booking_time}", "%Y-%m-%d %H:%M")
            
            availability = await db.check_availability(booking_datetime, party_size)
            
            if availability.available:
                return f"Great news! We have availability for {party_size} people on {booking_date} at {booking_time}."
            else:
                message = f"Sorry, we don't have availability for {party_size} people on {booking_date} at {booking_time}. "
                if availability.suggested_times:
                    suggestions = [t.strftime("%I:%M %p") for t in availability.suggested_times]
                    message += f"How about one of these alternative times: {', '.join(suggestions)}?"
                return message
                
        except ValueError:
            return "Please provide the date in YYYY-MM-DD format and time in HH:MM format (24-hour)."
        except Exception as e:
            return f"I'm sorry, there was an error checking availability: {str(e)}"

    async def find_booking_tool(self, confirmation_code: str) -> str:
        """Tool function to find a booking by confirmation code"""
        try:
            booking = await db.find_booking_by_confirmation(confirmation_code)
            if booking:
                return f"I found your booking: {booking.party_size} people on " \
                       f"{booking.booking_date.strftime('%B %d, %Y at %I:%M %p')}. " \
                       f"Status: {booking.status}."
            else:
                return "I couldn't find a booking with that confirmation code. Could you please double-check the code?"
        except Exception as e:
            return f"Error looking up booking: {str(e)}"

    async def cancel_booking_tool(self, confirmation_code: str) -> str:
        """Tool function to cancel a booking"""
        try:
            booking = await db.find_booking_by_confirmation(confirmation_code)
            if not booking:
                return "I couldn't find a booking with that confirmation code."
            
            if booking.status == BookingStatus.CANCELLED:
                return "This booking is already cancelled."
            
            response = await db.update_booking_status(booking.id, BookingStatus.CANCELLED)
            if response.success:
                return f"Your booking for {booking.party_size} people on " \
                       f"{booking.booking_date.strftime('%B %d, %Y at %I:%M %p')} has been cancelled."
            else:
                return "I'm sorry, there was an error cancelling your booking. Please try again."
                
        except Exception as e:
            return f"Error cancelling booking: {str(e)}"

    async def get_menu_info_tool(self, category: Optional[str] = None, search_term: Optional[str] = None) -> str:
        """Tool function to get menu information"""
        try:
            if search_term:
                menu_items = await db.search_menu_items(search_term)
                if menu_items:
                    response = f"Here are the menu items I found for '{search_term}':\n\n"
                    for item in menu_items:
                        response += f"• {item.item_name} - ${item.price}\n"
                        if item.description:
                            response += f"  {item.description}\n"
                        if item.allergens:
                            response += f"  Allergens: {', '.join(item.allergens)}\n"
                        response += "\n"
                    return response
                else:
                    return f"I couldn't find any menu items matching '{search_term}'. Would you like me to tell you about our menu categories?"
            
            menu_items = await db.get_menu(category=category)
            if not menu_items:
                return "I'm sorry, I don't have menu information available right now. Please ask your server when you arrive."
            
            if category:
                response = f"Here are our {category} options:\n\n"
            else:
                response = "Here's our menu:\n\n"
                categories = {}
                for item in menu_items:
                    if item.category not in categories:
                        categories[item.category] = []
                    categories[item.category].append(item)
                
                for cat, items in categories.items():
                    response += f"{cat.upper()}:\n"
                    for item in items[:3]:  # Limit to 3 items per category for voice
                        response += f"• {item.item_name} - ${item.price}\n"
                    response += "\n"
                
                return response
            
            for item in menu_items:
                response += f"• {item.item_name} - ${item.price}\n"
                if item.description:
                    response += f"  {item.description}\n"
                if item.allergens:
                    response += f"  Allergens: {', '.join(item.allergens)}\n"
                response += "\n"
            
            return response
            
        except Exception as e:
            return f"I'm sorry, there was an error getting menu information: {str(e)}"

    async def get_restaurant_info_tool(self, info_type: str = "general") -> str:
        """Tool function to get restaurant information (hours, location, ambience)"""
        try:
            restaurant = await db.get_restaurant()
            if not restaurant:
                return "I'm sorry, I don't have restaurant information available right now."
            
            if info_type.lower() in ["hours", "time", "open"]:
                response = f"Our operating hours are:\n\n"
                for day, hours in restaurant.opening_hours.items():
                    if hours.get("closed"):
                        response += f"{day.title()}: Closed\n"
                    else:
                        response += f"{day.title()}: {hours.get('open')} - {hours.get('close')}\n"
                return response
            
            elif info_type.lower() in ["location", "address", "where"]:
                return f"We're located at {restaurant.address}. You can reach us at {restaurant.phone}."
            
            elif info_type.lower() in ["ambience", "atmosphere", "vibe", "setting"]:
                return """Our restaurant offers a warm and elegant dining atmosphere perfect for any occasion. 
                We feature intimate lighting, comfortable seating, and a sophisticated yet welcoming environment. 
                Whether you're here for a romantic dinner, business lunch, or family celebration, 
                we strive to create the perfect ambience for your dining experience."""
            
            else:
                return f"""Welcome to {restaurant.name}! We're located at {restaurant.address}. 
                Our restaurant offers a warm, elegant atmosphere perfect for any dining occasion. 
                You can reach us at {restaurant.phone} for any questions."""
                
        except Exception as e:
            return f"I'm sorry, there was an error getting restaurant information: {str(e)}"

    async def handle_special_requests_tool(self, request_type: str, details: str) -> str:
        """Tool function to handle special requests, especially seating preferences"""
        try:
            manager_phone = os.getenv("MANAGER_PHONE", "+1234567890")
            
            if any(keyword in request_type.lower() for keyword in ["seat", "table", "location", "view", "private", "booth"]):
                return f"""I understand you have a special seating request: {details}. 
                For specific seating arrangements and table preferences, I'd be happy to connect you with our manager 
                who can ensure we accommodate your needs perfectly. 
                
                You can reach our manager directly at {manager_phone}, or I can note this request 
                and have them call you back. Which would you prefer?"""
            
            elif any(keyword in request_type.lower() for keyword in ["dietary", "allergy", "food", "kitchen"]):
                return f"""I've noted your dietary request: {details}. 
                Our kitchen team is very accommodating with dietary restrictions and allergies. 
                I'll make sure this information is included with your reservation. 
                
                For complex dietary needs, our manager at {manager_phone} can also discuss 
                specific preparation methods with our chef."""
            
            elif any(keyword in request_type.lower() for keyword in ["event", "celebration", "party", "special occasion"]):
                return f"""That sounds like a wonderful {request_type}! I've noted: {details}. 
                For special celebrations, our manager can help arrange decorations, special menus, 
                or other arrangements to make your event memorable. 
                
                Please call our manager at {manager_phone} to discuss the details, 
                or I can have them call you back."""
            
            else:
                return f"""I've noted your special request: {details}. 
                I'll include this with your reservation. For any complex arrangements, 
                our manager at {manager_phone} can assist you further."""
                
        except Exception as e:
            return f"I've noted your request and will include it with your reservation. Our staff will follow up with you."


async def entrypoint(ctx: agents.JobContext):
    # Extract phone number from room metadata if available
    phone_number = ctx.room.metadata.get("phone_number", "unknown")
    
    session = AgentSession(
        llm=google.beta.realtime.RealtimeModel(
            model="gemini-2.0-flash-exp",
            voice="Puck", 
            temperature=0.6,
            instructions="""You are a professional restaurant reservation assistant. You can help customers with:
            
            1. Making new reservations - ask for date, time, party size, name, and phone number
            2. Checking availability for specific dates and times
            3. Finding existing bookings with confirmation codes
            4. Canceling reservations
            5. Providing menu information and dietary guidance
            6. Sharing restaurant information (hours, location, ambience)
            7. Handling special requests and seating preferences
            
            Available tools:
            - create_booking_tool(customer_name, phone_number, booking_date, booking_time, party_size, special_requests)
            - check_availability_tool(booking_date, booking_time, party_size)  
            - find_booking_tool(confirmation_code)
            - cancel_booking_tool(confirmation_code)
            - get_menu_info_tool(category, search_term) - for menu questions
            - get_restaurant_info_tool(info_type) - for hours, location, ambience info
            - handle_special_requests_tool(request_type, details) - for seating preferences and special needs
            
            Date format: YYYY-MM-DD (e.g., 2024-12-25)
            Time format: HH:MM in 24-hour format (e.g., 19:30 for 7:30 PM)
            
            Always be friendly and professional. Confirm details before making bookings.
            For complex seating requests, route to manager contact."""
        )
    )

    # Create restaurant assistant
    assistant = RestaurantAssistant()
    
    # Start call tracking
    await assistant.start_call_tracking(phone_number)

    await session.start(
        room=ctx.room,
        agent=assistant,
    )

    await ctx.connect()

    # Register tools with the session
    session.register_tool(assistant.create_booking_tool)
    session.register_tool(assistant.check_availability_tool)
    session.register_tool(assistant.find_booking_tool)
    session.register_tool(assistant.cancel_booking_tool)
    session.register_tool(assistant.get_menu_info_tool)
    session.register_tool(assistant.get_restaurant_info_tool)
    session.register_tool(assistant.handle_special_requests_tool)

    await session.generate_reply(
        instructions="Greet the customer warmly and ask how you can help them with their restaurant reservation or any questions about our restaurant today."
    )


if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))