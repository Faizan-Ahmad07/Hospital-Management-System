import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Paper, Typography, Table, TableHead, TableRow, TableCell, TableBody, Button, Stack } from '@mui/material';
import { format } from 'date-fns';

interface Appointment { id: number; doctor_id: number; scheduled_time: string; status: string; }

const AppointmentsPage: React.FC = () => {
  const today = new Date();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ['appointments:list', today.toDateString()],
    queryFn: async () => {
      // reuse CSV export then parse minimal fields
      const d = today.toISOString().slice(0,10);
      const res = await axios.get(`/api/reports/appointments/export?date=${d}&format=csv`);
      const text: string = res.data || '';
      const lines: string[] = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
      if (!lines.length) return [] as Appointment[];
      const header = lines.shift()!.split(',');
      const idIdx = header.indexOf('id');
      const doctorIdx = header.indexOf('doctor_id');
      const timeIdx = header.indexOf('scheduled_time');
      const statusIdx = header.indexOf('status');
      if ([idIdx, doctorIdx, timeIdx, statusIdx].some(i => i === -1)) return [] as Appointment[];
      return lines.map((l: string) => {
        const parts = l.split(',');
        return {
          id: Number(parts[idIdx]),
          doctor_id: Number(parts[doctorIdx]),
          scheduled_time: parts[timeIdx],
          status: parts[statusIdx]
        } as Appointment;
      }).filter(a => !Number.isNaN(a.id));
    }
  });

  const approveMutation = useMutation({
    mutationFn: async (id: number) => {
      await axios.patch(`/api/appointments/${id}`, { status: 'approved' });
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['appointments:list'] })
  });

  return (
    <Paper sx={{ p:2 }}>
      <Typography variant="h6" gutterBottom>Today's Appointments</Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>ID</TableCell><TableCell>Doctor</TableCell><TableCell>Time</TableCell><TableCell>Status</TableCell><TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(data||[]).map(a => (
            <TableRow key={a.id}>
              <TableCell>{a.id}</TableCell>
              <TableCell>{a.doctor_id}</TableCell>
              <TableCell>{format(new Date(a.scheduled_time), 'HH:mm')}</TableCell>
              <TableCell>{a.status}</TableCell>
              <TableCell>
                <Stack direction="row" spacing={1}>
                  <Button size="small" disabled={a.status==='approved'} onClick={() => approveMutation.mutate(a.id)}>Approve</Button>
                </Stack>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Paper>
  );
};

export default AppointmentsPage;
