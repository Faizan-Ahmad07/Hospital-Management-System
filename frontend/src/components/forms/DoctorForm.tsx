import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Stack } from '@mui/material';

interface Props { open: boolean; onClose: () => void; onCreated?: () => void; }

const initial = { email: '', full_name: '', password: 'DocPass123', specialization: '' };

const DoctorForm: React.FC<Props> = ({ open, onClose, onCreated }) => {
  const [values, setValues] = React.useState(initial);
  const [loading, setLoading] = React.useState(false);
  const change = (e: React.ChangeEvent<HTMLInputElement>) => setValues(v => ({ ...v, [e.target.name]: e.target.value }));
  const submit = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: values.email, full_name: values.full_name, password: values.password, role: 'doctor' }) });
      if (!res.ok && res.status !== 400) throw new Error('register failed');
      // Assign specialization if admin (ignore failure silently)
      if (values.specialization) {
        const list = await fetch('/api/admin/doctors');
        if (list.ok) {
          const doctors = await list.json();
            const found = doctors.find((d: any) => d.email === values.email);
            if (found) {
              await fetch(`/api/admin/doctors/${found.id}/specialization?specialization=${encodeURIComponent(values.specialization)}`, { method: 'PATCH' });
            }
        }
      }
      onCreated && onCreated();
      setValues(initial);
      onClose();
    } catch (e) {
      alert('Create failed');
    } finally {
      setLoading(false);
    }
  };
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>New Doctor</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt:1 }}>
          <TextField label="Email" name="email" value={values.email} onChange={change} required fullWidth />
          <TextField label="Full Name" name="full_name" value={values.full_name} onChange={change} required fullWidth />
          <TextField label="Password" name="password" type="password" value={values.password} onChange={change} />
          <TextField label="Specialization" name="specialization" value={values.specialization} onChange={change} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={submit} disabled={loading || !values.email || !values.full_name} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );
};
export default DoctorForm;
