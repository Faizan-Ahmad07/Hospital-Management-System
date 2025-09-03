from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud, models, security, encryption
from app.schemas import (
    UserCreate, UserRead, LoginRequest, TokenPair, PatientCreate, AppointmentCreate,
    AppointmentUpdate, AppointmentRead, TokenRefreshRequest, HospitalCreate, HospitalRead,
    DoctorAvailabilityCreate, DoctorAvailabilityRead, DoctorRead, PatientUpdate, PatientProfile
)
from app.deps import get_current_user, RoleChecker

router = APIRouter()

# Admin role dependency instance (used in multiple endpoints)
admin_required = RoleChecker([models.UserRole.ADMIN])

@router.post("/auth/register", response_model=UserRead)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user_in.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db, user_in)

@router.post("/auth/login", response_model=TokenPair)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    access = security.create_access_token(str(user.id), user.role.value)
    refresh_token, jti = security.create_refresh_token(str(user.id), user.role.value)
    from datetime import datetime, timedelta
    crud.create_refresh_token_record(db, user.id, jti, datetime.utcnow() + timedelta(minutes=security.settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    return TokenPair(access_token=access, refresh_token=refresh_token)

@router.post("/auth/refresh", response_model=TokenPair)
def refresh_tokens(req: TokenRefreshRequest, db: Session = Depends(get_db)):
    payload = security.decode_token(req.refresh_token, refresh=True)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_id = int(payload.get("sub"))
    jti = payload.get("jti")
    user = db.get(models.User, user_id)
    if not user or not jti or not crud.validate_refresh_token(db, jti, user_id):
        raise HTTPException(status_code=401, detail="Token invalid or revoked")
    # rotate
    crud.revoke_refresh_token(db, jti)
    new_access = security.create_access_token(str(user.id), user.role.value)
    new_refresh_token, new_jti = security.create_refresh_token(str(user.id), user.role.value)
    from datetime import datetime, timedelta
    crud.create_refresh_token_record(db, user.id, new_jti, datetime.utcnow() + timedelta(minutes=security.settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    return TokenPair(access_token=new_access, refresh_token=new_refresh_token)

@router.post("/patients/register", response_model=UserRead)
def register_patient(data: PatientCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_patient_with_user(db, data)

@router.post("/appointments", response_model=AppointmentRead, dependencies=[Depends(RoleChecker([models.UserRole.PATIENT]))])
def create_appointment(appt_in: AppointmentCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.patient_profile:
        raise HTTPException(status_code=400, detail="Not a patient")
    try:
        appt = crud.create_appointment(db, current_user.patient_profile.id, appt_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return appt

@router.get("/appointments/{appt_id}", response_model=AppointmentRead)
def get_appointment(appt_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    appt = crud.get_appointment(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")
    # Access control
    if current_user.role == models.UserRole.PATIENT and appt.patient_id != current_user.patient_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if current_user.role == models.UserRole.DOCTOR and appt.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return appt

@router.patch("/appointments/{appt_id}", response_model=AppointmentRead)
def update_appointment(appt_id: int, appt_in: AppointmentUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    appt = crud.get_appointment(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")
    # Patients can only modify their own and only time or cancel
    if current_user.role == models.UserRole.PATIENT:
        if appt.patient_id != current_user.patient_profile.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        # restrict status changes by patient (can only cancel)
        if appt_in.status and appt_in.status not in [models.AppointmentStatus.CANCELLED.value]:
            raise HTTPException(status_code=400, detail="Invalid status change")
    # Doctors must own appointment
    if current_user.role == models.UserRole.DOCTOR and appt.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        appt = crud.update_appointment(db, appt, appt_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return appt

@router.patch("/patients/me", response_model=PatientProfile)
def update_patient(data: PatientUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != models.UserRole.PATIENT:
        raise HTTPException(status_code=403, detail="Forbidden")
    patient = crud.update_patient_profile(db, current_user, data)
    return PatientProfile(
        date_of_birth=patient.date_of_birth,
        contact_number=encryption.decrypt(patient.contact_number),
        address=encryption.decrypt(patient.address),
        emergency_contact=encryption.decrypt(patient.emergency_contact),
    )

@router.post("/admin/appointments/{appt_id}/reassign", response_model=AppointmentRead, dependencies=[Depends(admin_required)])
def reassign_appointment(appt_id: int, new_doctor_id: int, new_hospital_id: int | None = None, db: Session = Depends(get_db)):
    appt = crud.get_appointment(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")
    appt = crud.reassign_appointment(db, appt, new_doctor_id, new_hospital_id)
    return appt

@router.patch("/appointments/{appt_id}/doctor-note", response_model=AppointmentRead)
def update_doctor_note(appt_id: int, note: str = Form(...), current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    appt = crud.get_appointment(db, appt_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user.role != models.UserRole.DOCTOR or current_user.doctor_profile.id != appt.doctor_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    appt.notes = note
    db.commit()
    db.refresh(appt)
    return appt

@router.get("/reports/appointments/export")
def export_appointments(date: str, format: str = "csv", current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role not in [models.UserRole.ADMIN, models.UserRole.DOCTOR]:
        raise HTTPException(status_code=403, detail="Forbidden")
    from datetime import datetime as dt
    try:
        d = dt.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    if current_user.role == models.UserRole.DOCTOR:
        appts = crud.list_doctor_appointments_for_day(db, current_user.doctor_profile.id, d)
    else:
        start = d.replace(hour=0, minute=0, second=0)
        end = d.replace(hour=23, minute=59, second=59)
        from sqlalchemy import select
        appts = list(db.scalars(select(models.Appointment).where(models.Appointment.scheduled_time >= start, models.Appointment.scheduled_time <= end)))
    rows = ["id,doctor_id,patient_id,hospital_id,scheduled_time,status"]
    for a in appts:
        rows.append(f"{a.id},{a.doctor_id},{a.patient_id},{a.hospital_id or ''},{a.scheduled_time.isoformat()},{a.status.value}")
    csv_data = "\n".join(rows)
    if format == "csv":
        from fastapi.responses import StreamingResponse
        return StreamingResponse(iter([csv_data]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=appointments_{date}.csv"})
    elif format == "pdf":
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        text = c.beginText(40, 800)
        text.textLine(f"Appointments Report {date}")
        for line in rows:
            text.textLine(line)
            if text.getY() < 40:
                c.drawText(text)
                c.showPage()
                text = c.beginText(40, 800)
        c.drawText(text)
        c.showPage()
        c.save()
        buf.seek(0)
        from fastapi.responses import StreamingResponse
        return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=appointments_{date}.pdf"})
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

# --- Admin Endpoints ---

@router.post("/admin/hospitals", response_model=HospitalRead, dependencies=[Depends(admin_required)])
def create_hospital(hospital_in: HospitalCreate, db: Session = Depends(get_db)):
    return crud.create_hospital(db, hospital_in.name, hospital_in.address)

@router.get("/admin/hospitals", response_model=list[HospitalRead], dependencies=[Depends(admin_required)])
def list_hospitals(db: Session = Depends(get_db)):
    return crud.list_hospitals(db)

@router.get("/public/hospitals", response_model=list[HospitalRead])
def list_hospitals_public(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Any authenticated user can read
    return crud.list_hospitals(db)

@router.get("/admin/doctors", response_model=list[DoctorRead], dependencies=[Depends(admin_required)])
def list_doctors(db: Session = Depends(get_db)):
    doctors = crud.list_doctors(db)
    result = []
    for d in doctors:
        result.append(DoctorRead(id=d.id, user_id=d.user_id, specialization=d.specialization, full_name=d.user.full_name if d.user else None, email=d.user.email if d.user else None))
    return result

@router.get("/public/doctors", response_model=list[DoctorRead])
def list_doctors_public(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    doctors = crud.list_doctors(db)
    return [DoctorRead(id=d.id, user_id=d.user_id, specialization=d.specialization, full_name=d.user.full_name if d.user else None, email=d.user.email if d.user else None) for d in doctors]

@router.post("/admin/doctors/{doctor_id}/availability", response_model=DoctorAvailabilityRead, dependencies=[Depends(admin_required)])
def add_availability(doctor_id: int, data: DoctorAvailabilityCreate, db: Session = Depends(get_db)):
    if doctor_id != data.doctor_id:
        raise HTTPException(status_code=400, detail="Doctor ID mismatch")
    availability = crud.add_doctor_availability(db, data.doctor_id, data.day_of_week, data.start_time, data.end_time)
    return availability

@router.patch("/admin/doctors/{doctor_id}/specialization", response_model=DoctorRead, dependencies=[Depends(admin_required)])
def set_doctor_specialization(doctor_id: int, specialization: str, db: Session = Depends(get_db)):
    try:
        doctor = crud.update_doctor_specialization(db, doctor_id, specialization)
    except ValueError:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return DoctorRead(id=doctor.id, user_id=doctor.user_id, specialization=doctor.specialization, full_name=doctor.user.full_name if doctor.user else None, email=doctor.user.email if doctor.user else None)

@router.get("/admin/doctors/{doctor_id}/availability", response_model=list[DoctorAvailabilityRead], dependencies=[Depends(admin_required)])
def list_availability(doctor_id: int, db: Session = Depends(get_db)):
    return crud.list_doctor_availability(db, doctor_id)

@router.get("/reports/doctor-schedule", response_model=list[AppointmentRead])
def doctor_schedule(doctor_id: int, date: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Access: doctor self or admin
    if current_user.role == models.UserRole.DOCTOR and current_user.doctor_profile.id != doctor_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if current_user.role not in [models.UserRole.DOCTOR, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        from datetime import datetime as dt
        date_obj = dt.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format; use YYYY-MM-DD")
    appts = crud.list_doctor_appointments_for_day(db, doctor_id, date_obj)
    return appts
