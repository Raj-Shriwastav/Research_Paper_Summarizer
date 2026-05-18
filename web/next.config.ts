import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  compress: true,
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'higxlckrcpqxhodibmax.supabase.co',
        pathname: '/**',
      },
    ],
  },
};

export default nextConfig;
