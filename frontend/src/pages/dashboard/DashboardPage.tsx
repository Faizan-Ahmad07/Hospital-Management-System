import React from 'react';
import { Grid, Paper, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

interface AppointmentEntry { id: number; doctor_id: number; status: string; }

const DashboardPage: React.FC = () => {
  // Fetch today's appointments to build quick charts
  const today = new Date().toISOString().slice(0,10);
  const { data: appointments } = useQuery({
    queryKey: ['appointments', today],
    queryFn: async () => {
      const res = await axios.get(`/api/reports/appointments/export?date=${today}&format=csv`);
      const text: string = res.data || '';
      const lines: string[] = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
      if (!lines.length) return [] as AppointmentEntry[];
      const header = lines.shift()!.split(',');
      const statusIdx = header.indexOf('status');
      const doctorIdx = header.indexOf('doctor_id');
      const idIdx = header.indexOf('id');
      // If mandatory columns missing, bail out gracefully
      if (statusIdx === -1 || doctorIdx === -1 || idIdx === -1) return [] as AppointmentEntry[];
      const entries: AppointmentEntry[] = lines.map((l: string) => {
        const parts = l.split(',');
        return {
          id: Number(parts[idIdx]),
            doctor_id: Number(parts[doctorIdx]),
            status: parts[statusIdx]
        };
      }).filter(e => !Number.isNaN(e.id));
      return entries;
    }
  });

  const statusCounts = (appointments || []).reduce<Record<string, number>>((acc: Record<string, number>, a: AppointmentEntry) => {
    acc[a.status] = (acc[a.status] || 0) + 1; return acc;
  }, {} as Record<string, number>);
  const statusData = Object.entries(statusCounts).map(([name, value]) => ({ name, value }));

  const doctorCounts = (appointments || []).reduce<Record<number, number>>((acc: Record<number, number>, a: AppointmentEntry) => {
    acc[a.doctor_id] = (acc[a.doctor_id] || 0) + 1; return acc;
  }, {} as Record<number, number>);
  const doctorData = Object.entries(doctorCounts).map(([id, value]) => ({ doctor: Number(id), value }));

  const COLORS = ['#1976d2','#9c27b0','#ff9800','#2e7d32','#d32f2f'];

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={4}>
        <Paper sx={{ p:2 }}>
          <Typography variant="h6">Today Status Mix</Typography>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={statusData} dataKey="value" nameKey="name" outerRadius={80} label>
                {statusData.map((entry, idx) => (
                  <Cell key={`c-${idx}`} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </Paper>
      </Grid>
      <Grid item xs={12} md={8}>
        <Paper sx={{ p:2 }}>
          <Typography variant="h6">Appointments per Doctor</Typography>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={doctorData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="doctor" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#1976d2" />
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </Grid>
    </Grid>
  );
};

export default DashboardPage;
