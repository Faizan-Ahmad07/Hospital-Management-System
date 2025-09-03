from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient_profile: Mapped["Patient"] = relationship("Patient", back_populates="user", uselist=False)
    doctor_profile: Mapped["Doctor"] = relationship("Doctor", back_populates="user", uselist=False)

class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    date_of_birth: Mapped[str | None] = mapped_column(String(20))
    contact_number: Mapped[str | None] = mapped_column(String(255))  # encrypted
    address: Mapped[str | None] = mapped_column(String(255))  # encrypted
    emergency_contact: Mapped[str | None] = mapped_column(String(255))  # encrypted

    user: Mapped[User] = relationship("User", back_populates="patient_profile")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    specialization: Mapped[str | None] = mapped_column(String(100))

    user: Mapped[User] = relationship("User", back_populates="doctor_profile")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="doctor")
    availabilities: Mapped[list["DoctorAvailability"]] = relationship("DoctorAvailability", back_populates="doctor")
    assignments: Mapped[list["DoctorHospitalAssignment"]] = relationship("DoctorHospitalAssignment", back_populates="doctor")

class Hospital(Base):
    __tablename__ = "hospitals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    address: Mapped[str | None] = mapped_column(String(255))

    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="hospital")
    doctor_assignments: Mapped[list["DoctorHospitalAssignment"]] = relationship("DoctorHospitalAssignment", back_populates="hospital")

class DoctorHospitalAssignment(Base):
    __tablename__ = "doctor_hospital_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id", ondelete="CASCADE"))
    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="assignments")
    hospital: Mapped[Hospital] = relationship("Hospital", back_populates="doctor_assignments")

class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[AppointmentStatus] = mapped_column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    patient: Mapped[Patient] = relationship("Patient", back_populates="appointments")
    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="appointments")
    hospital: Mapped[Hospital] = relationship("Hospital", back_populates="appointments")

class DoctorAvailability(Base):
    __tablename__ = "doctor_availabilities"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    day_of_week: Mapped[int] = mapped_column(Integer)  # 0-6
    start_time: Mapped[str] = mapped_column(String(5))  # HH:MM
    end_time: Mapped[str] = mapped_column(String(5))

    doctor: Mapped[Doctor] = relationship("Doctor", back_populates="availabilities")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user: Mapped[User] = relationship("User")
