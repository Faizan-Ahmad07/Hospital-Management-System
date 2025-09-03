import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  role: string | null;
  userEmail: string | null;
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const STORAGE_KEY = 'hms_auth_state_v1';

function loadStoredState(): AuthState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { accessToken: null, refreshToken: null, role: null, userEmail: null };
    const parsed = JSON.parse(raw);
    return {
      accessToken: parsed.accessToken || null,
      refreshToken: parsed.refreshToken || null,
      role: parsed.role || null,
      userEmail: parsed.userEmail || null
    };
  } catch {
    return { accessToken: null, refreshToken: null, role: null, userEmail: null };
  }
}

function persistState(state: AuthState) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* ignore */ }
}

function decodeExp(token: string | null): number | null {
  if (!token) return null;
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    if (typeof payload.exp === 'number') return payload.exp; // seconds
  } catch { /* ignore */ }
  return null;
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>(() => loadStoredState());
  const refreshingRef = useRef<Promise<string | null> | null>(null);
  const expTimerRef = useRef<number | null>(null);

  const setAndPersist = useCallback((updater: AuthState | ((prev: AuthState) => AuthState)) => {
    setState(prev => {
      const next = typeof updater === 'function' ? (updater as (p: AuthState) => AuthState)(prev) : updater;
      persistState(next);
      return next;
    });
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await axios.post('/api/auth/login', { email, password });
    setAndPersist({
      accessToken: res.data.access_token,
      refreshToken: res.data.refresh_token,
      role: res.data.role,
      userEmail: email
    });
    axios.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;
  }, [setAndPersist]);

  const logout = useCallback(() => {
    setAndPersist({ accessToken: null, refreshToken: null, role: null, userEmail: null });
    delete axios.defaults.headers.common['Authorization'];
    if (expTimerRef.current) {
      window.clearTimeout(expTimerRef.current);
      expTimerRef.current = null;
    }
  }, [setAndPersist]);

  const performRefresh = useCallback(async (): Promise<string | null> => {
    if (!state.refreshToken) return null;
    if (refreshingRef.current) return refreshingRef.current; // in-flight
    refreshingRef.current = (async () => {
      try {
        const res = await axios.post('/api/auth/refresh', { refresh_token: state.refreshToken });
        const newAccess = res.data.access_token;
        const newRefresh = res.data.refresh_token || state.refreshToken; // rotation
        setAndPersist(prev => ({ ...prev, accessToken: newAccess, refreshToken: newRefresh }));
        axios.defaults.headers.common['Authorization'] = `Bearer ${newAccess}`;
        return newAccess;
      } catch (e) {
        logout();
        return null;
      } finally {
        refreshingRef.current = null;
      }
    })();
    return refreshingRef.current;
  }, [state.refreshToken, setAndPersist, logout]);

  // Axios response interceptor for 401 retry once
  useEffect(() => {
    const interceptor = axios.interceptors.response.use(r => r, async (error: AxiosError) => {
      const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
      if (error.response?.status === 401 && !original?._retry && state.refreshToken) {
        original._retry = true;
        const refreshed = await performRefresh();
        if (refreshed) {
          if (original.headers) {
            (original.headers as any).Authorization = `Bearer ${refreshed}`;
          } else {
            original.headers = { Authorization: `Bearer ${refreshed}` } as any;
          }
          return axios(original);
        }
      }
      return Promise.reject(error);
    });
    return () => axios.interceptors.response.eject(interceptor);
  }, [performRefresh, state.refreshToken]);

  // Proactive refresh 1 minute before expiry
  useEffect(() => {
    if (expTimerRef.current) {
      window.clearTimeout(expTimerRef.current);
      expTimerRef.current = null;
    }
    const exp = decodeExp(state.accessToken);
    if (!exp) return;
    const msUntil = exp * 1000 - Date.now() - 60_000; // 1 min early
    if (msUntil <= 0) {
      performRefresh();
      return;
    }
    expTimerRef.current = window.setTimeout(() => { performRefresh(); }, msUntil);
  }, [state.accessToken, performRefresh]);

  useEffect(() => {
    if (state.accessToken) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${state.accessToken}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }
  }, [state.accessToken]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, isAuthenticated: !!state.accessToken }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
