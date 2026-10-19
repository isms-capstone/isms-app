import { cpSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const root = process.cwd();
const server = resolve(root, ".next/standalone/server.js");
if (!existsSync(server)) throw new Error("Run npm run build before npm start.");
cpSync(resolve(root, "public"), resolve(root, ".next/standalone/public"), {
  recursive: true,
});
cpSync(
  resolve(root, ".next/static"),
  resolve(root, ".next/standalone/.next/static"),
  { recursive: true },
);
process.env.PORT ||= "3100";
process.env.HOSTNAME ||= "0.0.0.0";
await import(pathToFileURL(server).href);
