import React, { useState, useEffect } from 'react'
import AuthForm from './components/AuthForm'
import MapView from './components/MapView'

function App() {
  const [token, setToken] = useState(null)
  const [is2FAVerified, setIs2FAVerified] = useState(false)

  useEffect(() => {
    const savedToken = sessionStorage.getItem('token')
    const verified = sessionStorage.getItem('is_2fa_verified')
    if (savedToken && verified === 'true') {
      setToken(savedToken)
      setIs2FAVerified(true)
    }
  }, [])

  const handleAuthSuccess = (authToken, verified) => {
    setToken(authToken)
    setIs2FAVerified(verified)
    sessionStorage.setItem('token', authToken)
    sessionStorage.setItem('is_2fa_verified', verified.toString())
  }

  const handleLogout = async () => {
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
      } catch (err) {
        console.error('Logout error:', err)
      }
    }
    
    setToken(null)
    setIs2FAVerified(false)
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('is_2fa_verified')
  }

  if (!token || !is2FAVerified) {
    return <AuthForm onAuthSuccess={handleAuthSuccess} token={token} />
  }

  return <MapView token={token} onLogout={handleLogout} />
}

export default App
