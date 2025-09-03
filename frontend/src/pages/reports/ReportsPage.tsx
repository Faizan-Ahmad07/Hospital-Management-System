import React from 'react';
import { Paper, Typography, Button, Stack } from '@mui/material';

const ReportsPage: React.FC = () => {
  const today = new Date().toISOString().slice(0,10);
  const download = (format: 'csv'|'pdf') => {
    const url = `/api/reports/appointments/export?date=${today}&format=${format}`;
    window.open(url, '_blank');
  };
  return (
    <Paper sx={{ p:2 }}>
      <Typography variant="h6" gutterBottom>Reports</Typography>
      <Stack direction="row" spacing={2}>
        <Button variant="contained" onClick={() => download('csv')}>Download Today CSV</Button>
        <Button variant="outlined" onClick={() => download('pdf')}>Download Today PDF</Button>
      </Stack>
    </Paper>
  );
};
export default ReportsPage;
