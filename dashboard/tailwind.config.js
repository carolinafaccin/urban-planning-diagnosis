import { colors as wriColors } from "@wri-brasil/design-system";

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      // Cores lidas direto do pacote (fonte única) em vez de redigitadas —
      // evita a divergência silenciosa que já existe no dashboard do
      // climate-injustice-index (mesmos valores copiados à mão em 3 lugares).
      colors: { wri: wriColors },
      fontFamily: {
        sans: ["Arial", "Helvetica", "system-ui", "sans-serif"],
      },
    },
  },
  // Markdown (análise da área, notas metodológicas) usa a classe .prose-notes
  // (index.css, com os tokens da marca) em vez do plugin @tailwindcss/typography.
  plugins: [],
};
