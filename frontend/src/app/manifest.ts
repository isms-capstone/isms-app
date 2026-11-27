import type { MetadataRoute } from "next";

/** NFR-03: staff can install ISMS on a phone's home screen (PWA). */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Deverhood HT · ISMS",
    short_name: "ISMS",
    description: "บันทึกและติดตามเคสของทีมซัพพอร์ต",
    lang: "th",
    start_url: "/my-work",
    scope: "/",
    display: "standalone",
    background_color: "#ffffff",
    theme_color: "#0b60ff",
    icons: [
      { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "สร้างเคส", short_name: "สร้างเคส", url: "/cases/new" },
      { name: "งานของฉัน", short_name: "งานของฉัน", url: "/my-work" },
    ],
  };
}
