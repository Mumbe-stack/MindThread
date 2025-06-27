import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { writeFileSync, mkdirSync } from 'fs'
import { join } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Plugin to create _redirects file for Netlify SPA routing
    {
      name: 'netlify-spa-redirects',
      writeBundle(options) {
        const outDir = options.dir || 'dist'
        try {
          // Create the _redirects file for Netlify SPA routing
          const redirectsContent = '/*    /index.html   200\n'
          writeFileSync(join(outDir, '_redirects'), redirectsContent)
          console.log('✅ Created _redirects file for Netlify SPA routing')
        } catch (error) {
          console.log('⚠️ Could not create _redirects file:', error.message)
        }
      }
    }
  ],
  // Ensure environment variables are available
  define: {
    'process.env': process.env
  },
  // Build configuration
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
  // Development server configuration
  server: {
    port: 5173,
    host: true,
    proxy: {
      // Proxy API calls during development (optional)
      '/api': {
        target: 'https://mindthread-1.onrender.com',
        changeOrigin: true,
        secure: true,
      }
    }
  }
})