import React from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Stack } from '@mui/material';

export interface PatientFormValues {
  email: string; full_name: string; password: string; date_of_birth: string; contact_number: string; address: string; emergency_contact: string;
}

interface Props { open: boolean; onClose: () => void; onCreated?: () => void; }

const initial: PatientFormValues = { email: '', full_name: '', password: 'PatientPass123', date_of_birth: '1990-01-01', contact_number: '', address: '', emergency_contact: '' };

const PatientForm: React.FC<Props> = ({ open, onClose, onCreated }) => {
  const [values, setValues] = React.useState<PatientFormValues>(initial);
  const [loading, setLoading] = React.useState(false);
  const change = (e: React.ChangeEvent<HTMLInputElement>) => setValues(v => ({ ...v, [e.target.name]: e.target.value }));
  const submit = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/patients/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) });
      if (!res.ok) throw new Error('Failed');
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
      <DialogTitle>New Patient</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt:1 }}>
          <TextField label="Email" name="email" value={values.email} onChange={change} required fullWidth />
          <TextField label="Full Name" name="full_name" value={values.full_name} onChange={change} required fullWidth />
          <TextField label="Password" name="password" type="password" value={values.password} onChange={change} fullWidth />
          <TextField label="Date of Birth" name="date_of_birth" type="date" value={values.date_of_birth} onChange={change} InputLabelProps={{ shrink: true }} />
          <TextField label="Contact Number" name="contact_number" value={values.contact_number} onChange={change} />
          <TextField label="Address" name="address" value={values.address} onChange={change} multiline rows={2} />
          <TextField label="Emergency Contact" name="emergency_contact" value={values.emergency_contact} onChange={change} />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button onClick={submit} disabled={loading || !values.email || !values.full_name} variant="contained">Create</Button>
      </DialogActions>
    </Dialog>
  );
};
export default PatientForm;
