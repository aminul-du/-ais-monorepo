import path from 'node:path'
import type { NextConfig } from 'next'

const monorepoRoot = path.resolve(__dirname, '../..')

const nextConfig: NextConfig = {
  turbopack: {
    root: monorepoRoot,
  },
}

export default nextConfig
