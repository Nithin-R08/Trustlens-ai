import { cp, mkdir, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";

const source = path.resolve(".next");
const target = path.resolve("frontend", ".next");

if (!process.env.VERCEL || !existsSync(source)) {
  process.exit(0);
}

await rm(target, { recursive: true, force: true });
await mkdir(path.dirname(target), { recursive: true });
await cp(source, target, {
  recursive: true,
  filter: (item) => !item.includes(`${path.sep}.next${path.sep}cache${path.sep}`)
});

console.log("Prepared Vercel output fallback at frontend/.next");
