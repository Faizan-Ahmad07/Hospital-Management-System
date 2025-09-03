import requests, sys, time, json
from datetime import datetime, timedelta

BASE = "http://127.0.0.1:8000"

class Context:
    admin_token: str | None = None
    admin_refresh: str | None = None
    doctor_token: str | None = None
    doctor_refresh: str | None = None
    patient_token: str | None = None
    patient_refresh: str | None = None
    doctor_id: int | None = None
    hospital_id: int | None = None
    appointment_id: int | None = None

ctx = Context()


def pretty(label, obj):
    print(f"\n=== {label} ===")
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(obj)


def post(path, data=None, token=None, expect=200, content_type="application/json"):
    url = BASE + path
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type == "application/json":
        resp = requests.post(url, json=data, headers=headers)
    else:
        resp = requests.post(url, data=data, headers=headers)
    if resp.status_code != expect:
        pretty("ERROR RESPONSE", resp.text)
        raise SystemExit(f"POST {path} expected {expect} got {resp.status_code}")
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.text


def get(path, token=None, expect=200):
    url = BASE + path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers)
    if resp.status_code != expect:
        pretty("ERROR RESPONSE", resp.text)
        raise SystemExit(f"GET {path} expected {expect} got {resp.status_code}")
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.text


def patch(path, data=None, token=None, expect=200, content_type="application/json"):
    url = BASE + path
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type == "application/json":
        resp = requests.patch(url, json=data, headers=headers)
    else:
        resp = requests.patch(url, data=data, headers=headers)
    if resp.status_code != expect:
        pretty("ERROR RESPONSE", resp.text)
        raise SystemExit(f"PATCH {path} expected {expect} got {resp.status_code}")
    if resp.headers.get("content-type", "").startswith("application/json"):
        return resp.json()
    return resp.text


def step_register_users():
    # Admin
    admin_payload = {"email": "admin_auto@example.com", "full_name": "Auto Admin", "password": "AdminPass123", "role": "admin"}
    post("/auth/register", admin_payload, expect=200)
    # Doctor
    doctor_payload = {"email": "doctor_auto@example.com", "full_name": "Auto Doctor", "password": "DoctorPass123", "role": "doctor"}
    doc_resp = post("/auth/register", doctor_payload, expect=200)
    ctx.doctor_id = doc_resp.get("id")  # user id, doctor table id later fetched
    # Patient (self)
    patient_payload = {"email": "patient_auto@example.com", "full_name": "Auto Patient", "password": "PatientPass123"}
    post("/patients/register", patient_payload, expect=200)


def step_logins():
    def login(email, password):
        return post("/auth/login", {"email": email, "password": password}, expect=200)
    admin_tokens = login("admin_auto@example.com", "AdminPass123")
    ctx.admin_token = admin_tokens["access_token"]
    ctx.admin_refresh = admin_tokens["refresh_token"]
    doctor_tokens = login("doctor_auto@example.com", "DoctorPass123")
    ctx.doctor_token = doctor_tokens["access_token"]
    ctx.doctor_refresh = doctor_tokens["refresh_token"]
    patient_tokens = login("patient_auto@example.com", "PatientPass123")
    ctx.patient_token = patient_tokens["access_token"]
    ctx.patient_refresh = patient_tokens["refresh_token"]


def step_create_hospital():
    resp = post("/admin/hospitals", {"name": "Auto Hospital", "address": "Auto Way"}, token=ctx.admin_token)
    ctx.hospital_id = resp["id"]


def step_add_doctor_availability():
    # Need doctor_id from doctors listing (doctor table id not same as user id necessarily)
    doctors = get("/admin/doctors", token=ctx.admin_token)
    doc = next((d for d in doctors if d["email"] == "doctor_auto@example.com"), None)
    if not doc:
        raise SystemExit("Doctor not found in list")
    ctx.doctor_id = doc["id"]
    # Add availability for tomorrow weekday
    day_of_week = (datetime.utcnow() + timedelta(days=1)).weekday()
    post(f"/admin/doctors/{ctx.doctor_id}/availability", {
        "doctor_id": ctx.doctor_id,
        "day_of_week": day_of_week,
        "start_time": "08:00",
        "end_time": "17:00"
    }, token=ctx.admin_token)


def step_patient_book_appointment():
    # schedule at 09:30 tomorrow
    sched = (datetime.utcnow() + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
    resp = post("/appointments", {
        "doctor_id": ctx.doctor_id,
        "hospital_id": ctx.hospital_id,
        "scheduled_time": sched.isoformat()
    }, token=ctx.patient_token)
    ctx.appointment_id = resp["id"]


def step_doctor_add_note():
    patch(f"/appointments/{ctx.appointment_id}/doctor-note", {"note": "Initial assessment"}, token=ctx.doctor_token, content_type="application/x-www-form-urlencoded")


def step_doctor_schedule_report():
    appt_date = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
    sched = get(f"/reports/doctor-schedule?doctor_id={ctx.doctor_id}&date={appt_date}", token=ctx.doctor_token)
    pretty("Doctor Schedule", sched)


def step_export_csv():
    appt_date = (datetime.utcnow() + timedelta(days=1)).date().isoformat()
    resp = get(f"/reports/appointments/export?date={appt_date}&format=csv", token=ctx.admin_token)
    pretty("CSV Export", resp)


def step_refresh_token():
    new_tokens = post("/auth/refresh", {"refresh_token": ctx.patient_refresh}, expect=200)
    pretty("Rotated Tokens", new_tokens)


def run():
    print("Starting mock end-to-end flow against", BASE)
    step_register_users()
    step_logins()
    step_create_hospital()
    step_add_doctor_availability()
    step_patient_book_appointment()
    step_doctor_add_note()
    step_doctor_schedule_report()
    step_export_csv()
    step_refresh_token()
    print("\nAll steps completed successfully.")

if __name__ == "__main__":
    try:
        run()
    except SystemExit as e:
        print("FAILED:", e)
        sys.exit(1)
    except Exception as ex:
        print("UNEXPECTED ERROR:", ex)
        sys.exit(2)
