"""Comprehensive population & endpoint exercise script.
Run while API server is up at http://127.0.0.1:8000.

Creates:
- 1 admin
- N doctors with availability & random specializations
- H hospitals (assign appointments randomly among them)
- M patients (with profiles)
- Random appointments within availability windows
- Updates some appointments, doctor notes
- Exports CSV/PDF (CSV printed size only)
- Rotates refresh tokens

Usage:
  python backend/tests/populate_and_test.py --doctors 3 --patients 8 --days 2

"""
from __future__ import annotations
import argparse, random, json, time, os
from datetime import datetime, timedelta, timezone
import requests
from faker import Faker

BASE = "http://127.0.0.1:8000"
faker = Faker()


def _req(method: str, path: str, token: str | None = None, expect: int = 200, json_body=None, form_body=None):
    url = BASE + path
    headers = {}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        resp = requests.request(method, url, headers=headers, json=json_body)
    elif form_body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        resp = requests.request(method, url, headers=headers, data=form_body)
    else:
        resp = requests.request(method, url, headers=headers)
    if resp.status_code != expect:
        raise SystemExit(f"{method} {path} expected {expect} got {resp.status_code}: {resp.text}")
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.text

post = lambda *a, **k: _req("POST", *a, **k)
get = lambda *a, **k: _req("GET", *a, **k)
patch = lambda *a, **k: _req("PATCH", *a, **k)

# ---------------- Core Steps ----------------

def create_admin():
    email = "admin_pop@example.com"
    try:
        post("/auth/register", json_body={
            "email": email,
            "full_name": "Population Admin",
            "password": "AdminPass123",
            "role": "admin"
        })
    except SystemExit:
        # assume already exists -> ignore
        pass
    tokens = post("/auth/login", json_body={"email": email, "password": "AdminPass123"})
    return tokens["access_token"], tokens["refresh_token"]


SPECIALIZATIONS = [
    "cardiology", "neurology", "oncology", "pediatrics", "orthopedics",
    "dermatology", "psychiatry", "radiology", "surgery", "endocrinology"
]

def create_doctors(n: int, admin_token: str):
    """Register doctors (if not already) then assign random specializations via admin endpoint."""
    for i in range(n):
        email = f"doc_pop_{i}@example.com"
        try:
            post("/auth/register", json_body={
                "email": email,
                "full_name": faker.name(),
                "password": "DocPass123",
                "role": "doctor"
            })
        except SystemExit:
            # already exists
            pass
    listed = get("/admin/doctors", token=admin_token)
    doctor_entries = []
    for d in listed:
        if d.get("email", "").startswith("doc_pop_"):
            # assign / update specialization
            spec = random.choice(SPECIALIZATIONS)
            try:
                updated = patch(f"/admin/doctors/{d['id']}/specialization?specialization={spec}", token=admin_token)
                d = updated
            except SystemExit:
                # ignore failure; keep original
                d["specialization"] = d.get("specialization") or spec
            doctor_entries.append(d)
    return doctor_entries


def create_hospitals(admin_token: str, count: int):
    """Create multiple hospitals (idempotent). Returns list of hospital IDs."""
    existing = {h["name"]: h["id"] for h in get("/admin/hospitals", token=admin_token)}
    ids = []
    for i in range(count):
        name = f"Pop Hospital {i+1}" if count > 1 else "Pop Hospital"
        if name in existing:
            ids.append(existing[name])
            continue
        try:
            h = post("/admin/hospitals", token=admin_token, json_body={
                "name": name,
                "address": faker.address().replace('\n', ', ')
            })
            ids.append(h["id"])
        except SystemExit:
            # race or already exists, refetch
            refreshed = {h["name"]: h["id"] for h in get("/admin/hospitals", token=admin_token)}
            if name in refreshed:
                ids.append(refreshed[name])
            else:
                raise
    return ids


def add_availability_for_doctors(doctors, admin_token: str, days_span: int):
    # For each doctor create availability for each weekday in upcoming span
    created = 0
    base_day = datetime.now(timezone.utc).date()
    for d in doctors:
        for offset in range(days_span):
            day_date = base_day + timedelta(days=offset)
            day_of_week = day_date.weekday()  # 0-6
            # 09:00 - 17:00
            try:
                post(f"/admin/doctors/{d['id']}/availability", token=admin_token, json_body={
                    "doctor_id": d['id'],
                    "day_of_week": day_of_week,
                    "start_time": "09:00",
                    "end_time": "17:00"
                })
                created += 1
            except SystemExit:
                pass
    return created


def create_patients(m: int):
    """Create patients providing all profile fields, then patch profile to ensure encryption path exercised."""
    patient_tokens = []
    for i in range(m):
        email = f"pat_pop_{i}@example.com"
        dob = faker.date_of_birth(minimum_age=18, maximum_age=85).isoformat()
        contact = faker.phone_number()
        address = faker.address().replace('\n', ', ')
        emergency = faker.name() + " - " + faker.phone_number()
        payload = {
            "email": email,
            "full_name": faker.name(),
            "password": "PatientPass123",
            "date_of_birth": dob,
            "contact_number": contact,
            "address": address,
            "emergency_contact": emergency,
        }
        try:
            post("/patients/register", json_body=payload)
        except SystemExit:
            # already exists; continue
            pass
        tokens = post("/auth/login", json_body={"email": email, "password": "PatientPass123"})
        access_tok = tokens["access_token"]
        # patch again to cover update flow (random tweak to contact)
        patch("/patients/me", token=access_tok, json_body={
            "contact_number": contact + " ext" + str(i),
            "address": address,
            "emergency_contact": emergency,
            "date_of_birth": dob,
        })
        patient_tokens.append(access_tok)
    return patient_tokens


def book_random_appointments(patient_tokens, doctors, hospital_ids: list[int], per_patient: int):
    appt_ids = []
    for p_tok in patient_tokens:
        for _ in range(per_patient):
            d = random.choice(doctors)
            # choose a day among availability span (assumes availability created for first X days)
            day_offset = random.randint(0, 1)
            base_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_offset)
            hour = random.randint(9, 16)
            minute = random.choice([0, 30])
            scheduled = base_time.replace(hour=hour, minute=minute)
            try:
                resp = post("/appointments", token=p_tok, json_body={
                    "doctor_id": d['id'],
                    "hospital_id": random.choice(hospital_ids),
                    "scheduled_time": scheduled.isoformat()
                })
                appt_ids.append(resp["id"])
            except SystemExit as e:
                # conflict or availability failure; skip
                continue
    return appt_ids


def add_doctor_notes_and_status(doctors, admin_token: str):
    """Doctors add notes and update status for their appointments (approve first few). Returns count of notes updated."""
    note_updates = 0
    for d in doctors:
        tokens = post("/auth/login", json_body={"email": d['email'], "password": "DocPass123"})
        access = tokens["access_token"]
        today = datetime.now(timezone.utc).date().isoformat()
        schedule = get(f"/reports/doctor-schedule?doctor_id={d['id']}&date={today}", token=access)
        if not schedule:
            continue
        for idx, appt in enumerate(schedule[:3]):  # handle first 3
            patch(f"/appointments/{appt['id']}", token=access, json_body={"status": "approved", "notes": f"Approved visit #{idx+1}"})
            patch(f"/appointments/{appt['id']}/doctor-note", token=access, form_body={"note": f"Detailed clinical note for appointment {appt['id']}"})
            note_updates += 1
    return note_updates


def export_reports(admin_token: str, output_dir: str):
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now(timezone.utc).date().isoformat()
    # CSV
    csv_data = get(f"/reports/appointments/export?date={today}&format=csv", token=admin_token)
    csv_path = os.path.join(output_dir, f"appointments_{today}.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(csv_data)
    # PDF
    pdf_resp = requests.get(f"{BASE}/reports/appointments/export?date={today}&format=pdf", headers={"Authorization": f"Bearer {admin_token}"})
    if pdf_resp.status_code == 200 and pdf_resp.headers.get("content-type", "").startswith("application/pdf"):
        pdf_path = os.path.join(output_dir, f"appointments_{today}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_resp.content)
        pdf_size = len(pdf_resp.content)
    else:
        pdf_path = None
        pdf_size = 0
    print(f"CSV saved -> {csv_path} ({len(csv_data)} chars); PDF saved -> {pdf_path or 'N/A'} ({pdf_size} bytes)")
    return csv_path, pdf_path, len(csv_data), pdf_size


def refresh_one_patient(patient_tokens):
    # Just refresh first patient
    if not patient_tokens:
        return
    # Need refresh token -> relogin
    email = "pat_pop_0@example.com"
    tokens = post("/auth/login", json_body={"email": email, "password": "PatientPass123"})
    refreshed = post("/auth/refresh", json_body={"refresh_token": tokens['refresh_token']})
    print("Refreshed patient access token length:", len(refreshed['access_token']))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--doctors", type=int, default=2)
    parser.add_argument("--patients", type=int, default=5)
    parser.add_argument("--days", type=int, default=2, help="availability span days")
    parser.add_argument("--hospitals", type=int, default=2, help="number of hospitals to create")
    parser.add_argument("--per-patient", type=int, default=3, help="appointments per patient target")
    # On-demand additions (short-circuit normal flow if provided)
    parser.add_argument("--add-doctor", type=str, help="Add a single doctor: email[:Full Name][:specialization]")
    parser.add_argument("--add-patient", type=str, help="Add a single patient: email[:Full Name]")
    parser.add_argument("--add-appointment", type=str, help="Add appointment: patient_email:doctor_email:YYYY-MM-DDTHH:MM[:hospital_id]")
    parser.add_argument("--patient-password", type=str, default="PatientPass123", help="Password to use for new / existing patients when adding appointment")
    parser.add_argument("--doctor-password", type=str, default="DocPass123", help="Password for new / existing doctor creation")
    args = parser.parse_args()

    print("== Population & Test Script ==")
    admin_access, _ = create_admin()
    print("Admin ready")

    # Short-circuit feature additions
    if args.add_doctor or args.add_patient or args.add_appointment:
        # Ensure at least one hospital exists for appointment additions
        hospitals_existing = create_hospitals(admin_access, max(1, args.hospitals))
        if args.add_doctor:
            parts = args.add_doctor.split(":")
            d_email = parts[0]
            d_name = parts[1] if len(parts) > 1 and parts[1] else faker.name()
            d_spec = parts[2] if len(parts) > 2 and parts[2] else random.choice(SPECIALIZATIONS)
            try:
                post("/auth/register", json_body={
                    "email": d_email,
                    "full_name": d_name,
                    "password": args.doctor_password,
                    "role": "doctor"
                })
            except SystemExit:
                pass
            # fetch doctor id and set specialization
            listed = get("/admin/doctors", token=admin_access)
            target = next((x for x in listed if x.get("email") == d_email), None)
            if target:
                try:
                    patch(f"/admin/doctors/{target['id']}/specialization?specialization={d_spec}", token=admin_access)
                except SystemExit:
                    pass
            print(f"Doctor ensured: {d_email} ({d_spec})")
        if args.add_patient:
            parts = args.add_patient.split(":")
            p_email = parts[0]
            p_name = parts[1] if len(parts) > 1 and parts[1] else faker.name()
            dob = faker.date_of_birth(minimum_age=18, maximum_age=85).isoformat()
            contact = faker.phone_number()
            address = faker.address().replace('\n', ', ')
            emergency = faker.name() + " - " + faker.phone_number()
            try:
                post("/patients/register", json_body={
                    "email": p_email,
                    "full_name": p_name,
                    "password": args.patient_password,
                    "date_of_birth": dob,
                    "contact_number": contact,
                    "address": address,
                    "emergency_contact": emergency,
                })
            except SystemExit:
                pass
            print(f"Patient ensured: {p_email}")
        if args.add_appointment:
            # patient_email:doctor_email:ISO[:hospital_id]
            parts = args.add_appointment.split(":")
            if len(parts) < 3:
                raise SystemExit("--add-appointment format invalid. Use patient_email:doctor_email:YYYY-MM-DDTHH:MM[:hospital_id]")
            p_email, d_email, iso_time = parts[0], parts[1], parts[2]
            hospital_id = int(parts[3]) if len(parts) > 3 else hospitals_existing[0]
            # login patient to get access token
            try:
                p_tokens = post("/auth/login", json_body={"email": p_email, "password": args.patient_password})
            except SystemExit:
                raise SystemExit("Patient login failed - ensure patient exists or correct password via --patient-password")
            access_tok = p_tokens["access_token"]
            # get doctor id
            listed = get("/admin/doctors", token=admin_access)
            doc = next((x for x in listed if x.get("email") == d_email), None)
            if not doc:
                raise SystemExit("Doctor email not found for appointment")
            try:
                resp = post("/appointments", token=access_tok, json_body={
                    "doctor_id": doc['id'],
                    "hospital_id": hospital_id,
                    "scheduled_time": iso_time
                })
                print(f"Appointment created id={resp['id']}")
            except SystemExit as e:
                raise SystemExit(f"Failed to create appointment: {e}")
        print("Done single additions.")
        return

    doctors = create_doctors(args.doctors, admin_access)
    print(f"Doctors present: {len(doctors)}")

    hospital_ids = create_hospitals(admin_access, args.hospitals)
    print("Hospital ids:", hospital_ids)

    created_av = add_availability_for_doctors(doctors, admin_access, args.days)
    print("Availability entries attempted:", created_av)

    patient_tokens = create_patients(args.patients)
    print(f"Patients active: {len(patient_tokens)}")

    appts = book_random_appointments(patient_tokens, doctors, hospital_ids, args.per_patient)
    print(f"Appointments created: {len(appts)}")

    notes_updated = add_doctor_notes_and_status(doctors, admin_access)
    print(f"Doctor notes & status updates applied: {notes_updated}")

    out_dir = os.path.join(os.path.dirname(__file__), "output")
    csv_path, pdf_path, csv_len, pdf_len = export_reports(admin_access, out_dir)
    refresh_one_patient(patient_tokens)

    # Summary JSON
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "doctors": len(doctors),
        "patients": len(patient_tokens),
    "appointments_created": len(appts),
    "hospitals": len(hospital_ids),
    "doctor_specializations": {d.get("email"): d.get("specialization") for d in doctors},
        "doctor_notes_updates": notes_updated,
        "csv_report_path": csv_path,
        "pdf_report_path": pdf_path,
        "csv_length": csv_len,
        "pdf_length": pdf_len,
        "availability_entries_attempted": created_av,
    }
    summary_path = os.path.join(out_dir, "population_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written -> {summary_path}")

    print("Done.")

if __name__ == "__main__":
    main()
