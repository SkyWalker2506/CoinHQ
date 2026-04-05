import bundleAnalyzer from "@next/bundle-analyzer";

const withBundleAnalyzer = bundleAnalyzer({
  enabled: process.env.ANALYZE === "true",
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  // "standalone" is for Docker/self-hosted. Vercel handles output automatically.
  // output: "standalone",
};

export default withBundleAnalyzer(nextConfig);
