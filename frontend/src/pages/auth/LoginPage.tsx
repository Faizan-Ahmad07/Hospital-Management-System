import React from 'react';
import { useForm } from 'react-hook-form';
import { Box, Paper, TextField, Button, Typography } from '@mui/material';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

interface LoginForm {
  email: string;
  password: string;
}

const LoginPage: React.FC = () => {
  const { register, handleSubmit } = useForm<LoginForm>();
  const { login } = useAuth();
  const navigate = useNavigate();

  const onSubmit = async (data: LoginForm) => {
    try {
      await login(data.email, data.password);
      navigate('/');
    } catch (e: any) {
      alert(e.message || 'Login failed');
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
      <Paper sx={{ p: 4, width: 360 }} component="form" onSubmit={handleSubmit(onSubmit)}>
        <Typography variant="h6" gutterBottom>Login</Typography>
        <TextField label="Email" fullWidth margin="normal" {...register('email', { required: true })} />
        <TextField label="Password" type="password" fullWidth margin="normal" {...register('password', { required: true })} />
        <Button type="submit" variant="contained" fullWidth sx={{ mt: 2 }}>Login</Button>
      </Paper>
    </Box>
  );
};

export default LoginPage;
