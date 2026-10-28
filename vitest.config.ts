import { defineConfig } from 'vitest/config'
export default defineConfig({
  test: {
    env: { VITE_USE_MOCK: 'true' },
    include: ['frontend/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./frontend/test/setup.ts'],
  },
})
