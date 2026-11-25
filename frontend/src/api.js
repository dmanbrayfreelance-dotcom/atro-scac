import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export const analyzeContract = async (sourceCode, filename = 'Contract.sol') => {
  const response = await api.post('/analyze', {
    source_code: sourceCode,
    filename: filename,
  });
  return response.data;
};

export const analyzeUploadedFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/analyze/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getSamples = async () => {
  const response = await api.get('/samples');
  return response.data;
};

export const getSampleById = async (id) => {
  const response = await api.get(`/samples/${id}`);
  return response.data;
};

export const getAuditDb = async () => {
  const response = await api.get('/audit-db');
  return response.data;
};

export const addAuditDbEntry = async (entry) => {
  const response = await api.post('/audit-db', entry);
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get('/history');
  return response.data;
};

export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
