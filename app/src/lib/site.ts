/** Public host and origin. Override with VITE_SITE_HOST when self-hosting, so the provenance
 *  stamps (export.ts) and the absolute tags (og:image, og:url, canonical) name the same host. */
export const SITE_HOST: string = import.meta.env.VITE_SITE_HOST ?? 'makroskop.nodalit.com';
export const SITE_URL = `https://${SITE_HOST}`;
