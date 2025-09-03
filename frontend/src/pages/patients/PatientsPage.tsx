import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Paper, Typography, Table, TableHead, TableRow, TableCell, TableBody } from '@mui/material';

interface PatientRow { id: number; user_id: number; full_name?: string; email?: string; }

const PatientsPage: React.FC = () => {
  const { data } = useQuery({
    queryKey: ['patients'],
    queryFn: async () => {
      // (No dedicated endpoint created earlier for listing patients; placeholder.)
      return [] as PatientRow[];
    }
  });
  return (
    <Paper sx={{ p:2 }}>
      <Typography variant="h6" gutterBottom>Patients</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell><TableCell>Name</TableCell><TableCell>Email</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(data||[]).map(p => (
            <TableRow key={p.id}>
              <TableCell>{p.id}</TableCell>
              <TableCell>{p.full_name}</TableCell>
              <TableCell>{p.email}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
};
export default PatientsPage;
