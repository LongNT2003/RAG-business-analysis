const config = {
    development: {
        frontendUrl: 'http://localhost:5000',
        backendUrl: 'http://localhost:3000',
        apiUrl: 'http://localhost:5011',
        liveDevelopment: 'http://127.0.0.1:5502/frontend'
    },
    production: {
        frontendUrl: 'http://103.253.20.13:5000',
        backendUrl: 'http://103.253.20.13:3000',
        apiUrl: 'http://103.253.20.13:5011'
    }
};

// Determine environment based on hostname
export const getEnvironment = () => {
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'development';
    }
    return 'production';
};

export const getConfig = () => {
    const env = getEnvironment();
    return config[env];
};