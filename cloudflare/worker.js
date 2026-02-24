/**
 * Cloudflare Worker for path-based routing
 *
 * Routes:
 *   /docs/*  → docs service
 *   /api/*   → backend service
 *   /*       → frontend service
 *
 * Setup:
 *   1. Create worker in Cloudflare dashboard
 *   2. Set environment variables (DOCS_ORIGIN, API_ORIGIN, FRONTEND_ORIGIN)
 *   3. Add route: ambactracker.com/* → this worker
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Determine which origin to use
    let origin;

    if (path.startsWith('/docs')) {
      origin = env.DOCS_ORIGIN || 'https://docs.railway.internal';
    } else if (path.startsWith('/api') || path.startsWith('/auth') || path.startsWith('/admin')) {
      origin = env.API_ORIGIN || 'https://api.railway.internal';
    } else {
      origin = env.FRONTEND_ORIGIN || 'https://frontend.railway.internal';
    }

    // Build the new URL
    const targetUrl = new URL(path + url.search, origin);

    // Forward the request
    const response = await fetch(targetUrl, {
      method: request.method,
      headers: request.headers,
      body: request.body,
    });

    return response;
  }
}
