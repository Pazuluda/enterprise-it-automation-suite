import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/static/app/',
  plugins: [react()],
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/app-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'assets/styles-[hash].css'
          }

          return 'assets/[name]-[hash][extname]'
        },
        manualChunks(id) {
          const file = id.replaceAll('\\', '/')

          if (file.includes('node_modules')) {
            if (file.includes('/react/') || file.includes('/react-dom/')) {
              return 'vendor-react'
            }

            return 'vendor'
          }

          if (file.includes('/src/features/agent/')) {
            return 'feature-agent'
          }

          if (file.includes('/src/features/active-directory/')) {
            return 'feature-active-directory'
          }

          if (file.includes('/src/features/employee-lifecycle/')) {
            return 'feature-employee-lifecycle'
          }

          if (file.includes('/src/features/overview/')) {
            return 'feature-overview'
          }

          if (file.includes('/src/features/requests/')) {
            return 'feature-requests'
          }

          if (file.includes('/src/features/admin/')) {
            return 'feature-admin'
          }

          if (file.includes('/src/components/')) {
            return 'shared-components'
          }

          if (file.includes('/src/utils/')) {
            return 'shared-utils'
          }
        }
      }
    }
  }
})
