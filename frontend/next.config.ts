import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  outputFileTracingRoot: path.join(__dirname),
  webpack: (config) => {
    config.resolve = config.resolve ?? {};
    config.resolve.alias = {
      ...(config.resolve.alias ?? {}),
      "@splinetool/react-spline": path.join(__dirname, "node_modules/@splinetool/react-spline/dist/react-spline.js"),
      "@splinetool/react-spline/next": path.join(
        __dirname,
        "node_modules/@splinetool/react-spline/dist/react-spline-next.js"
      )
    };
    return config;
  }
};

export default nextConfig;
