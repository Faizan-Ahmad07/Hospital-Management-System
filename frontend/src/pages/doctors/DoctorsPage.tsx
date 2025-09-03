import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Paper, Typography, Table, TableHead, TableRow, TableCell, TableBody, Chip } from '@mui/material';

interface DoctorRow { id: number; specialization?: string; email?: string; full_name?: string; }

const DoctorsPage: React.FC = () => {
  const { data } = useQuery({
    queryKey: ['doctors'],
    queryFn: async () => {
      const res = await axios.get('/api/admin/doctors');
      return res.data as DoctorRow[];
    }
  });
  return (
    <Paper sx={{ p:2 }}>
      <Typography variant="h6" gutterBottom>Doctors</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell><TableCell>Name</TableCell><TableCell>Email</TableCell><TableCell>Specialization</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(data||[]).map(d => (
            <TableRow key={d.id}>
              <TableCell>{d.id}</TableCell>
              <TableCell>{d.full_name}</TableCell>
              <TableCell>{d.email}</TableCell>
              <TableCell>{d.specialization ? <Chip size="small" label={d.specialization} /> : '-'}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
};
export default DoctorsPage;
