import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initZodErrorMap } from './lib/zod-config'
import { installErrorLog } from './lib/error-log'

// Initialize custom Zod error messages
initZodErrorMap()

// Capture uncaught errors / unhandled rejections into a small ring buffer
// surfaced as `window.__errorLog()` for post-hoc diagnosis.
installErrorLog()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
