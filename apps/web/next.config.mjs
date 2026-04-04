/** @type {import('next').NextConfig} */
const nextConfig = {
  typedRoutes: true,
  transpilePackages: ["react-markdown", "remark-gfm"],
}

export default nextConfig
