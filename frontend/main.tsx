import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './src/App'
import { ToastProvider } from './src/components/ToastProvider'

const root = createRoot(document.getElementById('root')!)
root.render(
  <ToastProvider>
    <App />
  </ToastProvider>
)

