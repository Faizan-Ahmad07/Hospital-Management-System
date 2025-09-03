import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Stack, MenuItem } from '@mui/material';

interface Doctor { id: number; full_name?: string; email?: string; specialization?: string; }
interface Hospital { id: number; name: string; address?: string; }

interface Props { open: boolean; onClose: () => void; onCreated?: () => void; }

const AppointmentForm: React.FC<Props> = ({ open, onClose, onCreated }) => {
  const [patientEmail, setPatientEmail] = React.useState('');
  const [doctorId, setDoctorId] = React.useState<number | ''>('');
  const [hospitalId, setHospitalId] = React.useState<number | ''>('');
  const [dateTime, setDateTime] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [doctors, setDoctors] = React.useState<Doctor[]>([]);
  const [hospitals, setHospitals] = React.useState<Hospital[]>([]);

  React.useEffect(() => {
    if (open) {
      fetch('/api/public/doctors').then(r => r.ok ? r.json(): []).then(setDoctors).catch(()=>{});
      fetch('/api/public/hospitals').then(r => r.ok ? r.json(): []).then(setHospitals).catch(()=>{});
    }
  }, [open]);

  const submit = async () => {
    if (!patientEmail || !doctorId || !hospitalId || !dateTime) return;
    setLoading(true);
    try {
      const login = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: patientEmail, password: 'PatientPass123' }) });
      if (!login.ok) throw new Error('Patient login failed');
      const tokens = await login.json();
      const res = await fetch('/api/appointments', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tokens.access_token}` }, body: JSON.stringify({ doctor_id: doctorId, hospital_id: hospitalId, scheduled_time: dateTime }) });
      if (!res.ok) throw new Error('Create failed');
      onCreated && onCreated();
      setPatientEmail(''); setDoctorId(''); setHospitalId(''); setDateTime('');
      onClose();
    } catch (e:any) {
      alert(e.message || 'Failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>New Appointment</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt:1 }}>
          <TextField label="Patient Email" value={patientEmail} onChange={e=>setPatientEmail(e.target.value)} required />
          <TextField select label="Doctor" value={doctorId} onChange={e=>setDoctorId(Number(e.target.value))} required>
            {doctors.map(d => <MenuItem key={d.id} value={d.id}>{d.full_name || d.email} {d.specialization && `(${d.specialization})`}</MenuItem>)}
          </TextField>
          <TextField select label="Hospital" value={hospitalId} onChange={e=>setHospitalId(Number(e.target.value))} required>
            {hospitals.map(h => <MenuItem key={h.id} value={h.id}>{h.name}</MenuItem>)}
          </TextField>
          <TextField type="datetime-local" label="Scheduled Time" value={dateTime} onChange={e=>setDateTime(e.target.value)} InputLabelProps={{ shrink: true }} required />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={submit} disabled={loading} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );
};
export default AppointmentForm;
