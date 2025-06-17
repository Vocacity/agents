import asyncio
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

from livekit import agents, api
from livekit.agents import WorkerOptions, JobContext
from agent import entrypoint as agent_entrypoint
from database import db
from schema import (
    Customer, Booking, CallLog, Menu, Restaurant,
    BookingStatus, CallStatus, BookingResponse, AvailabilityResponse, CustomerResponse
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LiveKit configuration
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

# Manager contact information
MANAGER_PHONE = os.getenv("MANAGER_PHONE", "+1234567890")

# Global variables for agent management
worker_process = None
agent_sessions = {}


# Pydantic models for API
class BookingRequest(BaseModel):
    customer_name: str
    phone_number: str
    booking_date: str  # YYYY-MM-DD
    booking_time: str  # HH:MM
    party_size: int
    special_requests: Optional[str] = None


class AvailabilityRequest(BaseModel):
    booking_date: str  # YYYY-MM-DD
    booking_time: str  # HH:MM
    party_size: int


class CallStartRequest(BaseModel):
    phone_number: str
    room_name: Optional[str] = None


class CallEndRequest(BaseModel):
    call_log_id: int
    transcript: Optional[str] = None
    notes: Optional[str] = None


class MenuSearchRequest(BaseModel):
    search_term: Optional[str] = None
    category: Optional[str] = None


class SpecialRequestRequest(BaseModel):
    request_type: str
    details: str
    customer_phone: Optional[str] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager"""
    logger.info("Starting Restaurant Voice Agent Server...")
    
    # Initialize database connection
    try:
        # Test database connection
        restaurant = await db.get_restaurant()
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    yield
    
    logger.info("Shutting down Restaurant Voice Agent Server...")


# Create FastAPI app
app = FastAPI(
    title="Restaurant Voice Agent API",
    description="Backend API for restaurant voice agent with LiveKit integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        restaurant = await db.get_restaurant()
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "services": {
                "livekit": "configured" if LIVEKIT_API_KEY else "not_configured",
                "database": "connected",
                "agent": "ready"
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


# Agent management endpoints
@app.post("/agent/start-call")
async def start_agent_call(request: CallStartRequest):
    """Start a new agent call session"""
    try:
        if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
            raise HTTPException(
                status_code=500,
                detail="LiveKit credentials not configured"
            )
        
        # Create LiveKit room and token
        room_name = request.room_name or f"restaurant-call-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Here you would typically:
        # 1. Create a room in LiveKit
        # 2. Generate access tokens
        # 3. Start the agent
        
        # For now, we'll simulate the agent start
        call_log = await db.create_call_log(
            phone_number=request.phone_number,
            status=CallStatus.INCOMING
        )
        
        return {
            "success": True,
            "room_name": room_name,
            "call_log_id": call_log.id,
            "message": "Agent call session started"
        }
        
    except Exception as e:
        logger.error(f"Error starting agent call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/end-call")
async def end_agent_call(request: CallEndRequest):
    """End an agent call session"""
    try:
        call_log = await db.update_call_log(
            request.call_log_id,
            call_end=datetime.now().isoformat(),
            status=CallStatus.COMPLETED.value,
            transcript=request.transcript,
            agent_notes=request.notes
        )
        
        if call_log:
            return {
                "success": True,
                "call_log": call_log.dict(),
                "message": "Call ended successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Call log not found")
            
    except Exception as e:
        logger.error(f"Error ending agent call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Booking management endpoints
@app.post("/bookings", response_model=BookingResponse)
async def create_booking(request: BookingRequest) -> BookingResponse:
    """Create a new restaurant booking"""
    try:
        # Parse datetime
        booking_datetime = datetime.strptime(f"{request.booking_date} {request.booking_time}", "%Y-%m-%d %H:%M")
        
        # Get or create customer
        customer_response = await db.get_or_create_customer(request.phone_number, request.customer_name)
        if not customer_response.success:
            raise HTTPException(status_code=400, detail=customer_response.message)
        
        # Create booking
        booking_response = await db.create_booking(
            customer_id=customer_response.customer.id,
            booking_date=booking_datetime,
            party_size=request.party_size,
            special_requests=request.special_requests
        )
        
        return booking_response
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")
    except Exception as e:
        logger.error(f"Error creating booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bookings/check-availability", response_model=AvailabilityResponse)
async def check_availability(request: AvailabilityRequest) -> AvailabilityResponse:
    """Check table availability"""
    try:
        booking_datetime = datetime.strptime(f"{request.booking_date} {request.booking_time}", "%Y-%m-%d %H:%M")
        availability = await db.check_availability(booking_datetime, request.party_size)
        return availability
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date/time format")
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bookings/{confirmation_code}")
async def get_booking(confirmation_code: str):
    """Get booking by confirmation code"""
    try:
        booking = await db.find_booking_by_confirmation(confirmation_code)
        if booking:
            return {"success": True, "booking": booking.dict()}
        else:
            raise HTTPException(status_code=404, detail="Booking not found")
            
    except Exception as e:
        logger.error(f"Error getting booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/bookings/{confirmation_code}/cancel")
async def cancel_booking(confirmation_code: str):
    """Cancel a booking"""
    try:
        booking = await db.find_booking_by_confirmation(confirmation_code)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        response = await db.update_booking_status(booking.id, BookingStatus.CANCELLED)
        if response.success:
            return {"success": True, "message": "Booking cancelled", "booking": response.booking.dict()}
        else:
            raise HTTPException(status_code=400, detail=response.message)
            
    except Exception as e:
        logger.error(f"Error cancelling booking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Menu and restaurant info endpoints
@app.post("/menu/search")
async def search_menu(request: MenuSearchRequest):
    """Search menu items"""
    try:
        if request.search_term:
            menu_items = await db.search_menu_items(request.search_term)
        else:
            menu_items = await db.get_menu(category=request.category)
        
        return {
            "success": True,
            "items": [item.dict() for item in menu_items],
            "count": len(menu_items)
        }
        
    except Exception as e:
        logger.error(f"Error searching menu: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/restaurant/info")
async def get_restaurant_info():
    """Get restaurant information"""
    try:
        restaurant = await db.get_restaurant()
        if restaurant:
            return {
                "success": True,
                "restaurant": restaurant.dict(),
                "manager_phone": MANAGER_PHONE
            }
        else:
            raise HTTPException(status_code=404, detail="Restaurant information not found")
            
    except Exception as e:
        logger.error(f"Error getting restaurant info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/special-requests")
async def handle_special_request(request: SpecialRequestRequest):
    """Handle special requests and route to manager if needed"""
    try:
        # Log the special request
        if request.customer_phone:
            customer_response = await db.get_or_create_customer(request.customer_phone)
            if customer_response.success:
                # You could log this request in a special_requests table
                pass
        
        # Determine if manager contact is needed
        requires_manager = any(keyword in request.request_type.lower() 
                             for keyword in ["seat", "table", "private", "booth", "event", "celebration"])
        
        response_message = f"Request noted: {request.details}"
        if requires_manager:
            response_message += f" For this type of request, please contact our manager at {MANAGER_PHONE}"
        
        return {
            "success": True,
            "message": response_message,
            "requires_manager_contact": requires_manager,
            "manager_phone": MANAGER_PHONE if requires_manager else None
        }
        
    except Exception as e:
        logger.error(f"Error handling special request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Customer management endpoints
@app.get("/customers/{phone_number}")
async def get_customer(phone_number: str):
    """Get customer by phone number"""
    try:
        customer_response = await db.get_or_create_customer(phone_number)
        if customer_response.success:
            bookings = await db.get_customer_bookings(customer_response.customer.id)
            return {
                "success": True,
                "customer": customer_response.customer.dict(),
                "bookings": [booking.dict() for booking in bookings]
            }
        else:
            raise HTTPException(status_code=404, detail="Customer not found")
            
    except Exception as e:
        logger.error(f"Error getting customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics endpoints
@app.get("/analytics/calls")
async def get_call_analytics(days: int = 7):
    """Get call analytics for the past N days"""
    try:
        # This would typically query call logs from the database
        # For now, return a simple response
        return {
            "success": True,
            "period_days": days,
            "metrics": {
                "total_calls": 0,
                "completed_calls": 0,
                "missed_calls": 0,
                "average_duration": 0,
                "bookings_created": 0
            },
            "message": "Analytics feature coming soon"
        }
        
    except Exception as e:
        logger.error(f"Error getting call analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent control endpoints
@app.post("/agent/deploy")
async def deploy_agent():
    """Deploy the LiveKit agent worker"""
    global worker_process
    
    try:
        if worker_process and worker_process.poll() is None:
            return {"success": True, "message": "Agent is already running"}
        
        # In a real deployment, you'd start the agent worker process
        # For now, we'll simulate it
        logger.info("Agent deployment requested")
        
        return {
            "success": True,
            "message": "Agent deployment initiated",
            "status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error deploying agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/stop")
async def stop_agent():
    """Stop the LiveKit agent worker"""
    global worker_process
    
    try:
        # Stop the agent worker if running
        if worker_process and worker_process.poll() is None:
            worker_process.terminate()
            logger.info("Agent worker stopped")
        
        return {
            "success": True,
            "message": "Agent stopped",
            "status": "stopped"
        }
        
    except Exception as e:
        logger.error(f"Error stopping agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run the FastAPI server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 