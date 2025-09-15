import React from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { ToastProvider } from './components/ToastProvider'

const rootEl = document.getElementById('root')
if (rootEl) {
  const root = createRoot(rootEl)
  root.render(
    <React.StrictMode>
      <ToastProvider>
        <App />
      </ToastProvider>
    </React.StrictMode>
  )
}
