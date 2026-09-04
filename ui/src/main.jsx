import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { enableApiGatewayRouting } from './services/apiGateway.js'
import { ToastProvider } from './components/common/ToastProvider.jsx'

enableApiGatewayRouting()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ToastProvider>
      <App />
    </ToastProvider>
  </StrictMode>,
)
