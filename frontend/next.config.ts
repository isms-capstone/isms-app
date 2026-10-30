import type { NextConfig } from "next";
const config: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  turbopack: { root: process.cwd() },
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:3000";
    return [
      "/registry",
      "/registry/:path*",
      "/admin",
      "/admin/:path*",
      "/api/v1/:path*",
    ].map((source) => ({ source, destination: `${backend}${source}` }));
  },
};
export default config;
