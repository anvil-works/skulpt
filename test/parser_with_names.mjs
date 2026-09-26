// Full execution-suite coverage includes Python 2 fixtures with named escapes.
// This resolver is test-only; the runtime rollout continues to use lean core.
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
const directory = process.env.SKULPT_PARSER_DIR || "node_modules/@anvil-works/skulpt-parser/dist-core";
const core = await import(pathToFileURL(resolve(directory, "index.js")).href);
const { unicodeName } = await import(pathToFileURL(resolve(directory, "unicode-names.js")).href);
export const parseModule = (source, options) => core.parseModule(source, { ...options, unicodeName });
export const scan = core.scan;
