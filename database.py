import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import random
import string
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

from schema import (
    Customer, Restaurant, Table, Booking, CallLog, Menu,
    BookingStatus, CallStatus, TableSize,
    BookingResponse, AvailabilityResponse, CustomerResponse
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RestaurantDatabase:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("Connected to Supabase database")

    def generate_confirmation_code(self) -> str:
        """Generate a random 6-character confirmation code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    # Customer operations
    async def get_or_create_customer(self, phone_number: str, name: Optional[str] = None) -> CustomerResponse:
        """Get existing customer or create new one"""
        try:
            # Try to find existing customer
            result = self.supabase.table("customers").select("*").eq("phone_number", phone_number).execute()
            
            if result.data:
                customer = Customer(**result.data[0])
                return CustomerResponse(success=True, customer=customer, message="Customer found")
            
            # Create new customer
            customer_data = {
                "phone_number": phone_number,
                "name": name,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("customers").insert(customer_data).execute()
            
            if result.data:
                customer = Customer(**result.data[0])
                return CustomerResponse(success=True, customer=customer, message="New customer created")
            
            return CustomerResponse(success=False, message="Failed to create customer")
            
        except Exception as e:
            logger.error(f"Error in get_or_create_customer: {e}")
            return CustomerResponse(success=False, message=f"Database error: {str(e)}")

    async def update_customer(self, customer_id: int, **kwargs) -> CustomerResponse:
        """Update customer information"""
        try:
            kwargs["updated_at"] = datetime.now().isoformat()
            
            result = self.supabase.table("customers").update(kwargs).eq("id", customer_id).execute()
            
            if result.data:
                customer = Customer(**result.data[0])
                return CustomerResponse(success=True, customer=customer, message="Customer updated")
            
            return CustomerResponse(success=False, message="Customer not found")
            
        except Exception as e:
            logger.error(f"Error updating customer: {e}")
            return CustomerResponse(success=False, message=f"Database error: {str(e)}")

    # Restaurant operations
    async def get_restaurant(self, restaurant_id: int = 1) -> Optional[Restaurant]:
        """Get restaurant information (assuming single restaurant for now)"""
        try:
            result = self.supabase.table("restaurants").select("*").eq("id", restaurant_id).execute()
            
            if result.data:
                return Restaurant(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting restaurant: {e}")
            return None

    async def check_availability(self, booking_date: datetime, party_size: int, restaurant_id: int = 1) -> AvailabilityResponse:
        """Check table availability for given date and party size"""
        try:
            # Get restaurant info to check capacity and hours
            restaurant = await self.get_restaurant(restaurant_id)
            if not restaurant:
                return AvailabilityResponse(available=False, message="Restaurant not found")

            # Check if the requested time is within opening hours
            day_of_week = booking_date.strftime("%A").lower()
            opening_hours = restaurant.opening_hours.get(day_of_week)
            
            if not opening_hours or opening_hours.get("closed", False):
                return AvailabilityResponse(
                    available=False, 
                    message=f"Restaurant is closed on {day_of_week.title()}"
                )

            # Check for existing bookings at the same time
            start_time = booking_date - timedelta(hours=1)
            end_time = booking_date + timedelta(hours=2)
            
            result = self.supabase.table("bookings").select("party_size").gte(
                "booking_date", start_time.isoformat()
            ).lte(
                "booking_date", end_time.isoformat()
            ).eq("restaurant_id", restaurant_id).in_(
                "status", [BookingStatus.CONFIRMED.value, BookingStatus.PENDING.value]
            ).execute()

            total_booked = sum(booking["party_size"] for booking in result.data)
            
            if total_booked + party_size <= restaurant.max_capacity:
                return AvailabilityResponse(available=True, message="Table available")
            
            # Suggest alternative times
            suggested_times = []
            for hours_offset in [-1, 1, -2, 2, -3, 3]:
                alt_time = booking_date + timedelta(hours=hours_offset)
                if alt_time > datetime.now():  # Only future times
                    suggested_times.append(alt_time)
            
            return AvailabilityResponse(
                available=False,
                suggested_times=suggested_times[:3],
                message="Requested time not available. Here are some alternatives."
            )
            
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return AvailabilityResponse(available=False, message=f"Error checking availability: {str(e)}")

    async def create_booking(self, customer_id: int, booking_date: datetime, party_size: int, 
                           special_requests: Optional[str] = None, restaurant_id: int = 1) -> BookingResponse:
        """Create a new booking"""
        try:
            # Check availability first
            availability = await self.check_availability(booking_date, party_size, restaurant_id)
            if not availability.available:
                return BookingResponse(
                    success=False, 
                    message=availability.message
                )

            confirmation_code = self.generate_confirmation_code()
            
            booking_data = {
                "customer_id": customer_id,
                "restaurant_id": restaurant_id,
                "booking_date": booking_date.isoformat(),
                "party_size": party_size,
                "status": BookingStatus.PENDING.value,
                "special_requests": special_requests,
                "confirmation_code": confirmation_code,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("bookings").insert(booking_data).execute()
            
            if result.data:
                booking = Booking(**result.data[0])
                return BookingResponse(
                    success=True,
                    message="Booking created successfully",
                    booking=booking,
                    confirmation_code=confirmation_code
                )
            
            return BookingResponse(success=False, message="Failed to create booking")
            
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            return BookingResponse(success=False, message=f"Database error: {str(e)}")

    async def update_booking_status(self, booking_id: int, status: BookingStatus) -> BookingResponse:
        """Update booking status"""
        try:
            result = self.supabase.table("bookings").update({
                "status": status.value,
                "updated_at": datetime.now().isoformat()
            }).eq("id", booking_id).execute()
            
            if result.data:
                booking = Booking(**result.data[0])
                return BookingResponse(
                    success=True,
                    message=f"Booking status updated to {status.value}",
                    booking=booking
                )
            
            return BookingResponse(success=False, message="Booking not found")
            
        except Exception as e:
            logger.error(f"Error updating booking status: {e}")
            return BookingResponse(success=False, message=f"Database error: {str(e)}")

    async def get_customer_bookings(self, customer_id: int, include_past: bool = False) -> List[Booking]:
        """Get customer's bookings"""
        try:
            query = self.supabase.table("bookings").select("*").eq("customer_id", customer_id)
            
            if not include_past:
                query = query.gte("booking_date", datetime.now().isoformat())
            
            result = query.order("booking_date").execute()
            
            return [Booking(**booking) for booking in result.data]
            
        except Exception as e:
            logger.error(f"Error getting customer bookings: {e}")
            return []

    async def find_booking_by_confirmation(self, confirmation_code: str) -> Optional[Booking]:
        """Find booking by confirmation code"""
        try:
            result = self.supabase.table("bookings").select("*").eq("confirmation_code", confirmation_code).execute()
            
            if result.data:
                return Booking(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding booking by confirmation: {e}")
            return None

    # Call log operations
    async def create_call_log(self, phone_number: str, status: CallStatus, 
                            customer_id: Optional[int] = None, purpose: Optional[str] = None) -> CallLog:
        """Create a new call log entry"""
        try:
            call_data = {
                "customer_id": customer_id,
                "phone_number": phone_number,
                "call_start": datetime.now().isoformat(),
                "status": status.value,
                "purpose": purpose,
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("call_logs").insert(call_data).execute()
            
            if result.data:
                return CallLog(**result.data[0])
            
            raise Exception("Failed to create call log")
            
        except Exception as e:
            logger.error(f"Error creating call log: {e}")
            raise

    async def update_call_log(self, call_log_id: int, **kwargs) -> Optional[CallLog]:
        """Update call log entry"""
        try:
            if "call_end" in kwargs and "call_start" in kwargs:
                # Calculate duration if both start and end times are provided
                start_time = datetime.fromisoformat(kwargs["call_start"])
                end_time = datetime.fromisoformat(kwargs["call_end"])
                kwargs["duration_seconds"] = int((end_time - start_time).total_seconds())
            
            result = self.supabase.table("call_logs").update(kwargs).eq("id", call_log_id).execute()
            
            if result.data:
                return CallLog(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating call log: {e}")
            return None

    # Menu operations
    async def get_menu(self, restaurant_id: int = 1, category: Optional[str] = None) -> List[Menu]:
        """Get restaurant menu"""
        try:
            query = self.supabase.table("menu").select("*").eq("restaurant_id", restaurant_id).eq("is_available", True)
            
            if category:
                query = query.eq("category", category)
            
            result = query.order("category", "item_name").execute()
            
            return [Menu(**item) for item in result.data]
            
        except Exception as e:
            logger.error(f"Error getting menu: {e}")
            return []

    async def search_menu_items(self, search_term: str, restaurant_id: int = 1) -> List[Menu]:
        """Search menu items by name or description"""
        try:
            result = self.supabase.table("menu").select("*").eq("restaurant_id", restaurant_id).eq(
                "is_available", True
            ).or_(
                f"item_name.ilike.%{search_term}%,description.ilike.%{search_term}%"
            ).execute()
            
            return [Menu(**item) for item in result.data]
            
        except Exception as e:
            logger.error(f"Error searching menu items: {e}")
            return []

    async def seed_sample_menu(self, restaurant_id: int = 1) -> bool:
        """Seed sample menu data for testing"""
        try:
            sample_menu_items = [
                # Appetizers
                {
                    "restaurant_id": restaurant_id,
                    "category": "appetizers",
                    "item_name": "Truffle Arancini",
                    "description": "Crispy risotto balls with truffle oil and parmesan",
                    "price": 16.00,
                    "allergens": ["gluten", "dairy"],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "appetizers",
                    "item_name": "Burrata Caprese",
                    "description": "Fresh burrata with heirloom tomatoes and basil",
                    "price": 18.00,
                    "allergens": ["dairy"],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "appetizers",
                    "item_name": "Oysters on Half Shell",
                    "description": "Fresh daily selection with mignonette",
                    "price": 3.50,
                    "allergens": ["shellfish"],
                    "is_available": True
                },
                
                # Main Courses
                {
                    "restaurant_id": restaurant_id,
                    "category": "mains",
                    "item_name": "Dry-Aged Ribeye",
                    "description": "28-day aged ribeye with seasonal vegetables and red wine jus",
                    "price": 58.00,
                    "allergens": [],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "mains",
                    "item_name": "Pan-Seared Halibut",
                    "description": "Fresh halibut with lemon risotto and asparagus",
                    "price": 42.00,
                    "allergens": ["fish", "dairy"],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "mains",
                    "item_name": "Duck Confit",
                    "description": "Slow-cooked duck leg with cherry gastrique and roasted vegetables",
                    "price": 38.00,
                    "allergens": [],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "mains",
                    "item_name": "Lobster Ravioli",
                    "description": "House-made pasta with lobster in cream sauce",
                    "price": 36.00,
                    "allergens": ["shellfish", "gluten", "dairy", "eggs"],
                    "is_available": True
                },
                
                # Desserts
                {
                    "restaurant_id": restaurant_id,
                    "category": "desserts",
                    "item_name": "Chocolate Soufflé",
                    "description": "Warm chocolate soufflé with vanilla ice cream",
                    "price": 14.00,
                    "allergens": ["dairy", "eggs", "gluten"],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "desserts",
                    "item_name": "Tiramisu",
                    "description": "Classic Italian dessert with espresso and mascarpone",
                    "price": 12.00,
                    "allergens": ["dairy", "eggs", "gluten"],
                    "is_available": True
                },
                
                # Beverages
                {
                    "restaurant_id": restaurant_id,
                    "category": "beverages",
                    "item_name": "House Wine Selection",
                    "description": "Ask your server about our curated wine list",
                    "price": 12.00,
                    "allergens": ["sulfites"],
                    "is_available": True
                },
                {
                    "restaurant_id": restaurant_id,
                    "category": "beverages",
                    "item_name": "Craft Cocktails",
                    "description": "Signature cocktails made with premium spirits",
                    "price": 15.00,
                    "allergens": [],
                    "is_available": True
                }
            ]
            
            # Insert menu items
            result = self.supabase.table("menu").insert(sample_menu_items).execute()
            
            if result.data:
                logger.info(f"Successfully seeded {len(result.data)} menu items")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error seeding menu data: {e}")
            return False


# Global database instance
db = RestaurantDatabase() 