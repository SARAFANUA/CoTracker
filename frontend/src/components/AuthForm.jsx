import React, { useState } from 'react'

function AuthForm({ onAuthSuccess, token }) {
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    totpCode: ''
  })
  const [qrCodeUrl, setQrCodeUrl] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [showTOTP, setShowTOTP] = useState(false)

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
    setError('')
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    
    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Registration failed')
      }

      const data = await response.json()
      setQrCodeUrl(data.qr_code_url)
      setMessage('Scan QR code with authenticator app (e.g., Google Authenticator)')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: formData.username,
          password: formData.password
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Login failed')
      }

      const data = await response.json()
      setShowTOTP(true)
      onAuthSuccess(data.access_token, false)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleVerify2FA = async (e) => {
    e.preventDefault()
    setError('')

    try {
      const response = await fetch('/api/auth/verify-2fa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          totp_code: formData.totpCode
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || '2FA verification failed')
      }

      onAuthSuccess(token, true)
    } catch (err) {
      setError(err.message)
    }
  }

  if (showTOTP) {
    return (
      <div className="auth-container">
        <div className="auth-form">
          <h1>Two-Factor Authentication</h1>
          <form onSubmit={handleVerify2FA}>
            <div className="form-group">
              <label>Enter 6-digit code from authenticator app</label>
              <input
                type="text"
                name="totpCode"
                value={formData.totpCode}
                onChange={handleChange}
                placeholder="000000"
                maxLength="6"
                required
              />
            </div>
            {error && <div className="error-message">{error}</div>}
            <button type="submit" className="submit-btn">Verify</button>
          </form>
        </div>
      </div>
    )
  }

  if (qrCodeUrl) {
    return (
      <div className="auth-container">
        <div className="auth-form">
          <h1>Setup 2FA</h1>
          <div className="qr-code-container">
            <p>{message}</p>
            <img src={qrCodeUrl} alt="QR Code" />
            <p style={{fontSize: '12px', color: '#666', marginTop: '10px'}}>
              After scanning, login with your credentials
            </p>
          </div>
          <button 
            onClick={() => {
              setQrCodeUrl(null)
              setIsLogin(true)
              setMessage('')
            }} 
            className="submit-btn"
          >
            Continue to Login
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-container">
      <div className="auth-form">
        <h1>{isLogin ? 'Login' : 'Register'}</h1>
        <form onSubmit={isLogin ? handleLogin : handleRegister}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
            />
          </div>
          
          {!isLogin && (
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
            />
          </div>

          {error && <div className="error-message">{error}</div>}
          {message && <div className="success-message">{message}</div>}

          <button type="submit" className="submit-btn">
            {isLogin ? 'Login' : 'Register'}
          </button>
        </form>

        <div className="toggle-auth" onClick={() => setIsLogin(!isLogin)}>
          {isLogin ? 'Need an account? Register' : 'Have an account? Login'}
        </div>
      </div>
    </div>
  )
}

export default AuthForm
