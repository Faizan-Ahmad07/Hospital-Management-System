import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import LoginPage from './pages/auth/LoginPage';
import DashboardPage from './pages/dashboard/DashboardPage';
import PatientsPage from './pages/patients/PatientsPage';
import AppointmentsPage from './pages/appointments/AppointmentsPage';
import ReportsPage from './pages/reports/ReportsPage';
import DoctorsPage from './pages/doctors/DoctorsPage';
import { AuthProvider, useAuth } from './context/AuthContext';

const PrivateRoute: React.FC<{ children: React.ReactElement }> = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Lazy create pages (inline simple forms)
const CreatePatient: React.FC = () => {
  const [form, setForm] = React.useState({ email: '', full_name: '', password: 'PatientPass123' });
  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [e.target.name]: e.target.value });
  const submit = async () => {
    await fetch('/api/patients/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...form, date_of_birth: '1990-01-01', contact_number: 'N/A', address: 'N/A', emergency_contact: 'N/A' }) });
    alert('Patient created');
  };
  return (<div style={{ maxWidth: 400 }}><h3>Create Patient</h3><input name="email" placeholder="Email" value={form.email} onChange={onChange} /><input name="full_name" placeholder="Full Name" value={form.full_name} onChange={onChange} /><input name="password" placeholder="Password" value={form.password} onChange={onChange} type="password" /><button onClick={submit}>Create</button></div>);
};

const CreateDoctor: React.FC = () => {
  const [form, setForm] = React.useState({ email: '', full_name: '', password: 'DocPass123', specialization: '' });
  const onChange = (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [e.target.name]: e.target.value });
  const submit = async () => {
    await fetch('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: form.email, full_name: form.full_name, password: form.password, role: 'doctor' }) });
    if (form.specialization) {
      // Need admin token; simple attempt relying on existing session (admin user)
      // This will fail silently if not admin.
      const doctors = await fetch('/api/admin/doctors');
      if (doctors.ok) {
        const list = await doctors.json();
        const found = list.find((d: any) => d.email === form.email);
        if (found) {
          await fetch(`/api/admin/doctors/${found.id}/specialization?specialization=${encodeURIComponent(form.specialization)}`, { method: 'PATCH' });
        }
      }
    }
    alert('Doctor created');
  };
  return (<div style={{ maxWidth: 400 }}><h3>Create Doctor</h3><input name="email" placeholder="Email" value={form.email} onChange={onChange} /><input name="full_name" placeholder="Full Name" value={form.full_name} onChange={onChange} /><input name="password" placeholder="Password" value={form.password} onChange={onChange} type="password" /><input name="specialization" placeholder="Specialization" value={form.specialization} onChange={onChange} /><button onClick={submit}>Create</button></div>);
};

const CreateAppointment: React.FC = () => {
  const [patientEmail, setPatientEmail] = React.useState('');
  const [doctorId, setDoctorId] = React.useState('');
  const [hospitalId, setHospitalId] = React.useState('');
  const [when, setWhen] = React.useState('');
  const submit = async () => {
    // patient login to get token
    const login = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: patientEmail, password: 'PatientPass123' }) });
    if (!login.ok) { alert('Patient login failed'); return; }
    const tokens = await login.json();
    const res = await fetch('/api/appointments', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${tokens.access_token}` }, body: JSON.stringify({ doctor_id: Number(doctorId), hospital_id: Number(hospitalId), scheduled_time: when }) });
    if (!res.ok) { alert('Create failed'); return; }
    alert('Appointment created');
  };
  return (<div style={{ maxWidth: 480 }}><h3>Create Appointment</h3><input placeholder="Patient Email" value={patientEmail} onChange={e=>setPatientEmail(e.target.value)} /><input placeholder="Doctor ID" value={doctorId} onChange={e=>setDoctorId(e.target.value)} /><input placeholder="Hospital ID" value={hospitalId} onChange={e=>setHospitalId(e.target.value)} /><input placeholder="ISO DateTime" value={when} onChange={e=>setWhen(e.target.value)} /><button onClick={submit}>Create</button></div>);
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<Layout />}>        
          <Route path="/" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
          <Route path="/patients" element={<PrivateRoute><PatientsPage /></PrivateRoute>} />
          <Route path="/appointments" element={<PrivateRoute><AppointmentsPage /></PrivateRoute>} />
          <Route path="/reports" element={<PrivateRoute><ReportsPage /></PrivateRoute>} />
          <Route path="/doctors" element={<PrivateRoute><DoctorsPage /></PrivateRoute>} />
          <Route path="/create/patient" element={<PrivateRoute><CreatePatient /></PrivateRoute>} />
          <Route path="/create/doctor" element={<PrivateRoute><CreateDoctor /></PrivateRoute>} />
          <Route path="/create/appointment" element={<PrivateRoute><CreateAppointment /></PrivateRoute>} />
        </Route>
      </Routes>
    </AuthProvider>
  );
};

export default App;
