import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API functions
export const timesheetApi = {
  list: (params?: Record<string, any>) => api.get('/api/timesheets', { params }),
  get: (id: number) => api.get(`/api/timesheets/${id}`),
  create: (data: any) => api.post('/api/timesheets', data),
  update: (id: number, data: any) => api.put(`/api/timesheets/${id}`, data),
  delete: (id: number) => api.delete(`/api/timesheets/${id}`),
  summary: (params?: Record<string, any>) => api.get('/api/timesheets/summary', { params }),
};

export const invoiceApi = {
  list: (params?: Record<string, any>) => api.get('/api/invoices', { params }),
  get: (id: number) => api.get(`/api/invoices/${id}`),
  create: (data: any) => api.post('/api/invoices', data),
  update: (id: number, data: any) => api.put(`/api/invoices/${id}`, data),
  cancel: (id: number) => api.delete(`/api/invoices/${id}`),
  regeneratePdf: (id: number) => api.post(`/api/invoices/${id}/regenerate-pdf`),
};

export const userApi = {
  list: () => api.get('/api/users'),
  get: (id: number) => api.get(`/api/users/${id}`),
  update: (id: number, data: any) => api.put(`/api/users/${id}`, data),
  delete: (id: number) => api.delete(`/api/users/${id}`),
};
