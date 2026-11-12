import type { MetadataRoute } from "next";

const SITE = process.env.VERCEL_PROJECT_PRODUCTION_URL ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}` : "https://usevaluo.vercel.app";

/** Pages are open to crawlers; the API routes fetch live data and are rate limited, so they are left out. */
export default function robots(): MetadataRoute.Robots {
  return { rules: [{ userAgent: "*", allow: "/", disallow: "/api/" }], sitemap: `${SITE}/sitemap.xml` };
}
