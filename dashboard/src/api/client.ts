import axios from 'axios';

// Zwei separate API Clients
const coreApiClient = axios.create({
    baseURL: `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/api`,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
});

const backendPocClient = axios.create({
    baseURL: `${import.meta.env.VITE_CORE_API_URL || 'http://localhost:8001'}/api`,
    timeout: 10000,
    headers: { 'Content-Type': 'application/json' },
});

// Request Interceptor
coreApiClient.interceptors.request.use(
    (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => Promise.reject(error)
);

backendPocClient.interceptors.request.use(
    (config) => {
        console.log(`Backend PoC Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => Promise.reject(error)
);

// Response Interceptor
const responseHandler = (response: any) => response;
const errorHandler = (error: any) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
};

coreApiClient.interceptors.response.use(responseHandler, errorHandler);
backendPocClient.interceptors.response.use(responseHandler, errorHandler);

// Default Export: Core API (für Abwärtskompatibilität)
export const apiClient = coreApiClient;

// Named Exports
export { coreApiClient, backendPocClient };
