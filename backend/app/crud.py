from sqlalchemy.orm import Session
from sqlalchemy import select
from app import models, security
from app.schemas import UserCreate, PatientCreate, AppointmentCreate, AppointmentUpdate, PatientUpdate
from datetime import datetime, timedelta
from app import encryption
from typing import Optional, List

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.scalar(select(models.User).where(models.User.email == email))

def create_user(db: Session, user_in: UserCreate) -> models.User:
    hashed = security.hash_password(user_in.password)
    user = models.User(email=user_in.email, full_name=user_in.full_name, role=user_in.role, hashed_password=hashed)
    db.add(user)
    db.flush()
    if user_in.role == models.UserRole.PATIENT:
        patient = models.Patient(user_id=user.id)
        db.add(patient)
    elif user_in.role == models.UserRole.DOCTOR:
        doctor = models.Doctor(user_id=user.id)
        db.add(doctor)
    db.commit()
    db.refresh(user)
    return user

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not security.verify_password(password, user.hashed_password):
        return None
    return user

def create_patient_with_user(db: Session, patient_in: PatientCreate) -> models.User:
    user = models.User(email=patient_in.email, full_name=patient_in.full_name, role=models.UserRole.PATIENT, hashed_password=security.hash_password(patient_in.password))
    db.add(user)
    db.flush()
    patient = models.Patient(
        user_id=user.id,
        date_of_birth=patient_in.date_of_birth,
        contact_number=encryption.encrypt(patient_in.contact_number) if patient_in.contact_number else None,
        address=encryption.encrypt(patient_in.address) if patient_in.address else None,
        emergency_contact=encryption.encrypt(patient_in.emergency_contact) if patient_in.emergency_contact else None,
    )
    db.add(patient)
    db.commit()
    db.refresh(user)
    return user

def create_appointment(db: Session, patient_id: int, appt_in: AppointmentCreate) -> models.Appointment:
    _validate_appointment_slot(db, appt_in.doctor_id, patient_id, appt_in.scheduled_time)
    appt = models.Appointment(patient_id=patient_id, doctor_id=appt_in.doctor_id, hospital_id=appt_in.hospital_id, scheduled_time=appt_in.scheduled_time, status=models.AppointmentStatus.PENDING)
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt

def update_appointment(db: Session, appt: models.Appointment, appt_in: AppointmentUpdate) -> models.Appointment:
    if appt_in.scheduled_time is not None:
        _validate_appointment_slot(db, appt.doctor_id, appt.patient_id, appt_in.scheduled_time, exclude_id=appt.id)
        appt.scheduled_time = appt_in.scheduled_time
    if appt_in.status is not None:
        appt.status = models.AppointmentStatus(appt_in.status)
    if appt_in.notes is not None:
        appt.notes = appt_in.notes
    db.commit()
    db.refresh(appt)
    return appt

def get_appointment(db: Session, appt_id: int) -> Optional[models.Appointment]:
    return db.get(models.Appointment, appt_id)

# --- Admin / Hospital / Doctor Management ---
def create_hospital(db: Session, name: str, address: str | None = None) -> models.Hospital:
    hospital = models.Hospital(name=name, address=address)
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital

def list_hospitals(db: Session) -> list[models.Hospital]:
    return list(db.scalars(select(models.Hospital)))

def list_doctors(db: Session) -> list[models.Doctor]:
    return list(db.scalars(select(models.Doctor)))

def add_doctor_availability(db: Session, doctor_id: int, day_of_week: int, start_time: str, end_time: str) -> models.DoctorAvailability:
    avail = models.DoctorAvailability(doctor_id=doctor_id, day_of_week=day_of_week, start_time=start_time, end_time=end_time)
    db.add(avail)
    db.commit()
    db.refresh(avail)
    return avail

def list_doctor_availability(db: Session, doctor_id: int) -> list[models.DoctorAvailability]:
    stmt = select(models.DoctorAvailability).where(models.DoctorAvailability.doctor_id == doctor_id)
    return list(db.scalars(stmt))

def list_doctor_appointments_for_day(db: Session, doctor_id: int, date_day: datetime) -> list[models.Appointment]:
    start = datetime(date_day.year, date_day.month, date_day.day)
    end = start.replace(hour=23, minute=59, second=59)
    stmt = select(models.Appointment).where(models.Appointment.doctor_id == doctor_id, models.Appointment.scheduled_time >= start, models.Appointment.scheduled_time <= end)
    return list(db.scalars(stmt))

def update_patient_profile(db: Session, user: models.User, data: PatientUpdate) -> models.Patient:
    patient = user.patient_profile
    if not patient:
        raise ValueError("No patient profile")
    if data.date_of_birth is not None:
        patient.date_of_birth = data.date_of_birth
    if data.contact_number is not None:
        patient.contact_number = encryption.encrypt(data.contact_number)
    if data.address is not None:
        patient.address = encryption.encrypt(data.address)
    if data.emergency_contact is not None:
        patient.emergency_contact = encryption.encrypt(data.emergency_contact)
    db.commit()
    db.refresh(patient)
    return patient

def _validate_appointment_slot(db: Session, doctor_id: int, patient_id: int, scheduled_time: datetime, exclude_id: int | None = None):
    day = scheduled_time.weekday()
    time_str = scheduled_time.strftime("%H:%M")
    avail_stmt = select(models.DoctorAvailability).where(models.DoctorAvailability.doctor_id == doctor_id, models.DoctorAvailability.day_of_week == day)
    avail_list = list(db.scalars(avail_stmt))
    if not any(a.start_time <= time_str < a.end_time for a in avail_list):
        raise ValueError("Doctor not available at this time")
    window_start = scheduled_time - timedelta(minutes=29)
    window_end = scheduled_time + timedelta(minutes=29)
    stmt_conflict = select(models.Appointment).where(models.Appointment.doctor_id == doctor_id, models.Appointment.scheduled_time >= window_start, models.Appointment.scheduled_time <= window_end)
    if exclude_id:
        stmt_conflict = stmt_conflict.where(models.Appointment.id != exclude_id)
    if db.scalar(stmt_conflict):
        raise ValueError("Doctor has another appointment in that slot")
    stmt_p_conflict = select(models.Appointment).where(models.Appointment.patient_id == patient_id, models.Appointment.scheduled_time >= window_start, models.Appointment.scheduled_time <= window_end)
    if exclude_id:
        stmt_p_conflict = stmt_p_conflict.where(models.Appointment.id != exclude_id)
    if db.scalar(stmt_p_conflict):
        raise ValueError("Patient has another appointment in that slot")

def create_refresh_token_record(db: Session, user_id: int, jti: str, expires_at: datetime) -> models.RefreshToken:
    rec = models.RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

def revoke_refresh_token(db: Session, jti: str):
    rec = db.scalar(select(models.RefreshToken).where(models.RefreshToken.jti == jti))
    if rec and not rec.revoked:
        rec.revoked = True
        db.commit()

def validate_refresh_token(db: Session, jti: str, user_id: int) -> bool:
    rec = db.scalar(select(models.RefreshToken).where(models.RefreshToken.jti == jti, models.RefreshToken.user_id == user_id))
    if not rec or rec.revoked or rec.expires_at < datetime.utcnow():
        return False
    return True

def reassign_appointment(db: Session, appt: models.Appointment, new_doctor_id: int, new_hospital_id: int | None) -> models.Appointment:
    appt.doctor_id = new_doctor_id
    if new_hospital_id is not None:
        appt.hospital_id = new_hospital_id
    db.commit()
    db.refresh(appt)
    return appt

def update_doctor_specialization(db: Session, doctor_id: int, specialization: str | None) -> models.Doctor:
    doctor = db.get(models.Doctor, doctor_id)
    if not doctor:
        raise ValueError("Doctor not found")
    doctor.specialization = specialization
    db.commit()
    db.refresh(doctor)
    return doctor

