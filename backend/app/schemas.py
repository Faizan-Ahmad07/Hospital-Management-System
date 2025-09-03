from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from enum import Enum
from typing import Optional, List

class Role(str, Enum):
    patient = "patient"
    doctor = "doctor"
    admin = "admin"

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: Role

class UserCreate(UserBase):
    password: str = Field(min_length=8)

class UserRead(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class PatientProfile(BaseModel):
    date_of_birth: Optional[str]
    contact_number: Optional[str]
    address: Optional[str]
    emergency_contact: Optional[str]
    class Config:
        from_attributes = True

class DoctorProfile(BaseModel):
    specialization: Optional[str]
    class Config:
        from_attributes = True

class PatientCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    date_of_birth: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None

class PatientUpdate(BaseModel):
    date_of_birth: Optional[str]
    contact_number: Optional[str]
    address: Optional[str]
    emergency_contact: Optional[str]

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class AppointmentBase(BaseModel):
    doctor_id: int
    hospital_id: Optional[int]
    scheduled_time: datetime

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    scheduled_time: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class AppointmentRead(AppointmentBase):
    id: int
    patient_id: int
    status: str
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True

class DoctorAvailabilityCreate(BaseModel):
    doctor_id: int
    day_of_week: int
    start_time: str
    end_time: str

class DoctorAvailabilityRead(DoctorAvailabilityCreate):
    id: int
    class Config:
        from_attributes = True

class DoctorRead(BaseModel):
    id: int
    user_id: int
    specialization: str | None
    full_name: str | None = None
    email: str | None = None
    class Config:
        from_attributes = True

class HospitalCreate(BaseModel):
    name: str
    address: Optional[str]

class HospitalRead(HospitalCreate):
    id: int
    class Config:
        from_attributes = True
