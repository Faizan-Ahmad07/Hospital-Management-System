import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box, Button, Fab, Menu, MenuItem, ListItemIcon } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import MedicalInformationIcon from '@mui/icons-material/MedicalInformation';
import EventIcon from '@mui/icons-material/Event';
import { useAuth } from '../context/AuthContext';
import PatientForm from './forms/PatientForm';
import DoctorForm from './forms/DoctorForm';
import AppointmentForm from './forms/AppointmentForm';

const Layout: React.FC = () => {
  const { logout, userEmail, role } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [anchorEl, setAnchorEl] = React.useState<null|HTMLElement>(null);
  const [openPatient, setOpenPatient] = React.useState(false);
  const [openDoctor, setOpenDoctor] = React.useState(false);
  const [openAppt, setOpenAppt] = React.useState(false);

  const open = Boolean(anchorEl);
  const handleFab = (e: React.MouseEvent<HTMLElement>) => { setAnchorEl(e.currentTarget); };
  const closeMenu = () => setAnchorEl(null);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>Hospital Management</Typography>
          <Typography variant="body2" sx={{ mr: 2 }}>{userEmail} ({role})</Typography>
          <Button color="inherit" onClick={() => { logout(); navigate('/login'); }}>Logout</Button>
        </Toolbar>
      </AppBar>
      <Box sx={{ display: 'flex', flexGrow: 1 }}>
        <Box component="nav" sx={{ width: 220, borderRight: '1px solid #ddd', p: 2 }}>
          {[
            ['/', 'Dashboard'],
            ['/patients', 'Patients'],
            ['/appointments', 'Appointments'],
            ['/reports', 'Reports'],
            ['/doctors', 'Doctors']
          ].map(([path, label]) => (
            <Box key={path} sx={{ mb: 1 }}>
              <Link to={path} style={{
                textDecoration: location.pathname === path ? 'underline' : 'none'
              }}>{label}</Link>
            </Box>
          ))}
        </Box>
        <Box component="main" sx={{ flexGrow: 1, p: 3, position: 'relative' }}>
          <Outlet />
          <Fab color="primary" sx={{ position: 'fixed', bottom: 32, right: 32 }} onClick={handleFab}>
            <AddIcon />
          </Fab>
          <Menu anchorEl={anchorEl} open={open} onClose={closeMenu}>
            <MenuItem onClick={() => { closeMenu(); setOpenPatient(true); }}>
              <ListItemIcon><PersonAddIcon fontSize="small" /></ListItemIcon>
              New Patient
            </MenuItem>
            <MenuItem onClick={() => { closeMenu(); setOpenDoctor(true); }}>
              <ListItemIcon><MedicalInformationIcon fontSize="small" /></ListItemIcon>
              New Doctor
            </MenuItem>
            <MenuItem onClick={() => { closeMenu(); setOpenAppt(true); }}>
              <ListItemIcon><EventIcon fontSize="small" /></ListItemIcon>
              New Appointment
            </MenuItem>
          </Menu>
        </Box>
      </Box>
      <PatientForm open={openPatient} onClose={() => setOpenPatient(false)} />
      <DoctorForm open={openDoctor} onClose={() => setOpenDoctor(false)} />
      <AppointmentForm open={openAppt} onClose={() => setOpenAppt(false)} />
    </Box>
  );
};

export default Layout;
