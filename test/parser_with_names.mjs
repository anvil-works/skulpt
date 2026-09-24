// Full execution-suite coverage includes Python 2 fixtures with named escapes.
// This resolver is test-only; the runtime rollout continues to use lean core.
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
assert.ok(process.env.SKULPT_PARSER_DIR, "Set SKULPT_PARSER_DIR to the built parser dist-core directory");
const directory = process.env.SKULPT_PARSER_DIR;
const core = await import(pathToFileURL(resolve(directory, "index.js")).href);
const { unicodeName } = await import(pathToFileURL(resolve(directory, "unicode-names.js")).href);
export const parseModule = (source, options) => core.parseModule(source, { ...options, unicodeName });
export const scan = core.scan;
