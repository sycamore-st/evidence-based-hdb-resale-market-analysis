import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  outputFileTracingRoot: path.resolve(__dirname, "../.."),
  typedRoutes: true,
  transpilePackages: ["react-markdown", "remark-gfm"],
  env: {
    NEXT_PUBLIC_ASSET_VERSION: process.env.NEXT_PUBLIC_ASSET_VERSION
      ?? process.env.VERCEL_GIT_COMMIT_SHA
      ?? process.env.GITHUB_SHA
      ?? "",
  },
}

export default nextConfig
