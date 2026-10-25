import React from 'react'
import { createRoot } from 'react-dom/client'
import CustomerStore from './CustomerStore'
import './style.css'

createRoot(document.getElementById('root')!).render(<React.StrictMode><CustomerStore/></React.StrictMode>)
