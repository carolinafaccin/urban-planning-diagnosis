import { colors as wriColors } from "@wri-brasil/design-system";
import typography from "@tailwindcss/typography";

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
  plugins: [typography],
};
