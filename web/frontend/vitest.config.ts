import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(viteConfig, defineConfig({
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        '**/*.test.*',
        '**/__mocks__/**',
        '**/__tests__/**',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/locales/**',
      ],
    },
    deps: {
      optimizer: {
        web: {
          include: ['antd', '@ant-design/icons'],
        },
      },
    },
  },
}))
