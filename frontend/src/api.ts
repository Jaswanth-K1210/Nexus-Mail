import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    timeout: 30000,
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

// Handle 401 responses — try silent refresh, then redirect to login
let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function onRefreshed(token: string) {
    refreshSubscribers.forEach((cb) => cb(token));
    refreshSubscribers = [];
}

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        if (error.response?.status === 401 && !originalRequest._retry) {
            // Don't try to refresh the refresh request itself
            if (originalRequest.url?.includes('/auth/refresh')) {
                localStorage.removeItem('nexus_token');
                if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
                return Promise.reject(error);
            }

            if (isRefreshing) {
                // Queue this request until refresh completes
                return new Promise((resolve) => {
                    refreshSubscribers.push((token: string) => {
                        originalRequest.headers.Authorization = `Bearer ${token}`;
                        resolve(api(originalRequest));
                    });
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const token = localStorage.getItem('nexus_token');
                if (!token) throw new Error('No token');

                const res = await axios.post(
                    `${api.defaults.baseURL}/auth/refresh`,
                    {},
                    { headers: { Authorization: `Bearer ${token}` } }
                );

                const newToken = res.data.access_token;
                localStorage.setItem('nexus_token', newToken);
                isRefreshing = false;
                onRefreshed(newToken);

                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                return api(originalRequest);
            } catch {
                isRefreshing = false;
                refreshSubscribers = [];
                localStorage.removeItem('nexus_token');
                if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
                    window.location.href = '/login';
                }
                return Promise.reject(error);
            }
        }

        return Promise.reject(error);
    }
);

export default api;
