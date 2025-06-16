from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class CallStatus(str, Enum):
    INCOMING = "incoming"
    ANSWERED = "answered"
    MISSED = "missed"
    COMPLETED = "completed"
    FAILED = "failed"


class TableSize(str, Enum):
    SMALL = "2_people"      # 2 people
    MEDIUM = "4_people"     # 4 people
    LARGE = "6_people"      # 6 people
    EXTRA_LARGE = "8_plus"  # 8+ people


# Database Models
class Customer(BaseModel):
    id: Optional[int] = None
    phone_number: str = Field(..., description="Customer phone number")
    name: Optional[str] = Field(None, description="Customer name")
    email: Optional[str] = Field(None, description="Customer email")
    preferences: Optional[str] = Field(None, description="Dietary preferences or notes")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Restaurant(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., description="Restaurant name")
    address: str = Field(..., description="Restaurant address")
    phone: str = Field(..., description="Restaurant phone number")
    email: Optional[str] = Field(None, description="Restaurant email")
    opening_hours: dict = Field(..., description="Opening hours by day")
    max_capacity: int = Field(..., description="Maximum seating capacity")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Table(BaseModel):
    id: Optional[int] = None
    restaurant_id: int = Field(..., description="Restaurant ID")
    table_number: str = Field(..., description="Table identifier")
    capacity: int = Field(..., description="Number of seats")
    table_size: TableSize = Field(..., description="Table size category")
    is_available: bool = Field(True, description="Table availability")
    created_at: Optional[datetime] = None


class Booking(BaseModel):
    id: Optional[int] = None
    customer_id: int = Field(..., description="Customer ID")
    restaurant_id: int = Field(..., description="Restaurant ID")
    table_id: Optional[int] = Field(None, description="Assigned table ID")
    booking_date: datetime = Field(..., description="Date and time of booking")
    party_size: int = Field(..., description="Number of people")
    status: BookingStatus = Field(BookingStatus.PENDING, description="Booking status")
    special_requests: Optional[str] = Field(None, description="Special requests or notes")
    confirmation_code: Optional[str] = Field(None, description="Booking confirmation code")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CallLog(BaseModel):
    id: Optional[int] = None
    customer_id: Optional[int] = Field(None, description="Customer ID if known")
    phone_number: str = Field(..., description="Caller phone number")
    call_start: datetime = Field(..., description="Call start time")
    call_end: Optional[datetime] = Field(None, description="Call end time")
    duration_seconds: Optional[int] = Field(None, description="Call duration in seconds")
    status: CallStatus = Field(..., description="Call status")
    purpose: Optional[str] = Field(None, description="Purpose of call")
    booking_id: Optional[int] = Field(None, description="Related booking ID")
    transcript: Optional[str] = Field(None, description="Call transcript")
    agent_notes: Optional[str] = Field(None, description="Agent notes from the call")
    created_at: Optional[datetime] = None


class Menu(BaseModel):
    id: Optional[int] = None
    restaurant_id: int = Field(..., description="Restaurant ID")
    category: str = Field(..., description="Menu category (appetizers, mains, desserts, etc.)")
    item_name: str = Field(..., description="Menu item name")
    description: Optional[str] = Field(None, description="Item description")
    price: float = Field(..., description="Item price")
    allergens: Optional[List[str]] = Field(None, description="List of allergens")
    is_available: bool = Field(True, description="Item availability")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# Response Models
class BookingResponse(BaseModel):
    success: bool
    message: str
    booking: Optional[Booking] = None
    confirmation_code: Optional[str] = None


class AvailabilityResponse(BaseModel):
    available: bool
    suggested_times: Optional[List[datetime]] = None
    message: str


class CustomerResponse(BaseModel):
    success: bool
    customer: Optional[Customer] = None
    message: str


# SQL Schema for Supabase
SUPABASE_SCHEMA = """
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id BIGSERIAL PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    preferences TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Restaurants table
CREATE TABLE IF NOT EXISTS restaurants (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    phone VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    opening_hours JSONB NOT NULL,
    max_capacity INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tables table
CREATE TABLE IF NOT EXISTS tables (
    id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(id) ON DELETE CASCADE,
    table_number VARCHAR(50) NOT NULL,
    capacity INTEGER NOT NULL,
    table_size VARCHAR(20) NOT NULL CHECK (table_size IN ('2_people', '4_people', '6_people', '8_plus')),
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(restaurant_id, table_number)
);

-- Bookings table
CREATE TABLE IF NOT EXISTS bookings (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(id) ON DELETE CASCADE,
    restaurant_id BIGINT REFERENCES restaurants(id) ON DELETE CASCADE,
    table_id BIGINT REFERENCES tables(id) ON DELETE SET NULL,
    booking_date TIMESTAMP WITH TIME ZONE NOT NULL,
    party_size INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'cancelled', 'completed', 'no_show')),
    special_requests TEXT,
    confirmation_code VARCHAR(10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Call logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
    phone_number VARCHAR(20) NOT NULL,
    call_start TIMESTAMP WITH TIME ZONE NOT NULL,
    call_end TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    status VARCHAR(20) NOT NULL CHECK (status IN ('incoming', 'answered', 'missed', 'completed', 'failed')),
    purpose TEXT,
    booking_id BIGINT REFERENCES bookings(id) ON DELETE SET NULL,
    transcript TEXT,
    agent_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Menu table
CREATE TABLE IF NOT EXISTS menu (
    id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT REFERENCES restaurants(id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    allergens TEXT[],
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(booking_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_call_logs_phone ON call_logs(phone_number);
CREATE INDEX IF NOT EXISTS idx_call_logs_date ON call_logs(call_start);
CREATE INDEX IF NOT EXISTS idx_menu_restaurant ON menu(restaurant_id);

-- RLS (Row Level Security) policies can be added here if needed
-- ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Users can view their own data" ON customers FOR SELECT USING (auth.uid() = user_id);
""" 