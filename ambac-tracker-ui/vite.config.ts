import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig(({ mode }) => {
    // Load from .env files if available
    const env = loadEnv(mode, process.cwd(), '');
    console.log('Vite looking for .env in:', process.cwd());
    console.log('Your .env is probably in:', path.resolve(process.cwd(), '../'));

    // Fallback to actual process.env if not defined in .env
    const API_TARGET = env.VITE_API_TARGET || process.env.VITE_API_TARGET || "http://localhost:8000";

    if (!API_TARGET) {
        throw new Error('VITE_API_TARGET is not defined in .env or process.env');
    }

    return {
        plugins: [react(), tailwindcss()],
        resolve: {
            alias: {
                '@': path.resolve(__dirname, './src'),
            },
        },
        build: {
            sourcemap: true,
        },
        preview: {
            host: '0.0.0.0',
            port: 4173,
            allowedHosts: [env.FRONTEND_URL || 'localhost']
        },
        server: {
            host: '0.0.0.0',
            proxy: {
                '/api': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                },
                '/auth': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                },
                '/accounts': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                },
            },
        },
    };
});
