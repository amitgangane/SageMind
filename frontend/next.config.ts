import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,

  // Proxy API requests to backend to avoid CORS issues
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/v1/:path*",
      },
    ];
  },
};

export default nextConfig;
