import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Налаштування порту та хосту для frontend-сервера
    host: '0.0.0.0',
    port: 5000, // Frontend буде працювати на цьому порту
    proxy: {
      // Усі запити, що починаються з '/api', будуть перенаправлені
      '/api': {
        target: 'http://localhost:8000', // Адреса вашого backend-сервера
        changeOrigin: true, // Необхідно для правильної роботи проксі
        secure: false,      // Дозволяє запити до незахищеного http-сервера
      }
    }
  }
})