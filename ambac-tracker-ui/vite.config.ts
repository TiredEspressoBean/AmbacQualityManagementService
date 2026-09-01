import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig(({ mode }) => {
    // Load from .env files if available
    const env = loadEnv(mode, process.cwd(), '');
    // Dev diagnostic: console.warn('Vite looking for .env in:', process.cwd());

    // Fallback to actual process.env if not defined in .env.
    // 127.0.0.1, NOT localhost: on Windows, Node resolves localhost to ::1
    // intermittently while Django's runserver binds 127.0.0.1 only — the proxy
    // then surfaces random empty 500s / connection resets on parallel requests.
    // eslint-disable-next-line no-restricted-syntax -- dev-only default; .env is the real source in production
    const API_TARGET = env.VITE_API_TARGET || process.env.VITE_API_TARGET || "http://127.0.0.1:8000";

    // eslint-disable-next-line no-restricted-syntax -- dev-only default; .env is the real source in production
    const LANGGRAPH_API_TARGET = env.VITE_LANGGRAPH_API_URL || "http://127.0.0.1:2025"

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
        optimizeDeps: {
            include: [
                'react',
                'react-dom',
                '@tanstack/react-query',
                '@tanstack/react-router',
                '@tanstack/react-table',
                'three',
                'recharts',
                'framer-motion',
                'date-fns',
                'zod',
            ],
        },
        build: {
            sourcemap: true,
        },
        preview: {
            host: '0.0.0.0',
            port: 5173,
            allowedHosts: true,  // Allow all hosts (Railway generates dynamic subdomains)
        },
        server: {
            host: '0.0.0.0',
            https: false,
            proxy: {
                // agent:false on every Django-target entry: Node ≥19 enables
                // keep-alive on the global agent, and Django's runserver on
                // Windows intermittently RESETs reused sockets under parallel
                // load — surfacing as random empty 500s (ECONNRESET) that never
                // appear in Django's log. A fresh connection per request is
                // cheap on localhost and makes the proxy deterministic.
                '/api': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                    agent: false,
                },
                '/auth': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                    agent: false,
                },
                '/accounts': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                    agent: false,
                },
                '/media': {
                    target: API_TARGET,
                    changeOrigin: true,
                    secure: false,
                    agent: false,
                },
                "/lg": {
                    target: LANGGRAPH_API_TARGET,
                    changeOrigin: true,
                    secure: false,
                    rewrite: (p) => p.replace(/^\/lg/, ""),
                    configure: (proxy) => {
                        proxy.on('proxyReq', (proxyReq, req, res) => {
                            // Handle OPTIONS requests at proxy level
                            if (req.method === 'OPTIONS') {
                                res.writeHead(200, {
                                    'Access-Control-Allow-Origin': '*',
                                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
                                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                                    'Access-Control-Max-Age': '3600',
                                });
                                res.end();
                                return;
                            }
                        });
                    },
                },
            },
        },
    };
});
