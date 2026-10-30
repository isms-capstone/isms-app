import { resolve } from "node:path";
const config = {
  plugins: {
    [resolve(process.cwd(), "scripts/postcss-company-compat.cjs")]: {},
    "@tailwindcss/postcss": {},
  },
};
export default config;
