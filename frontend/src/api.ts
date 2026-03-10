import axios from 'axios';

const api = axios.create({
    baseURL: 'http://localhost:8000/api', // Backend URL
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add interceptor to include the JWT token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('nexus_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default api;
