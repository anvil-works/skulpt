// Shared legacy identifier rules for strings and the old tokenizer.
const Unicode = require("../support/polyfills/Unicode").default;

const { Lu, Ll, Lt, Lm, Lo, Nl, Mn, Mc, Nd, Pc } = Unicode;
const the_underscore = "_";
const Other_ID_Start = "\\u1885-\\u1886\\u2118\\u212E\\u309B-\\u309C";
const Other_ID_Continue = "\\u00B7\\u0387\\u1369-\\u1371\\u19DA";
const id_start = Lu + Ll + Lt + Lm + Lo + Nl + the_underscore + Other_ID_Start;
const id_continue = id_start + Mn + Mc + Nd + Pc + Other_ID_Continue;

const IDENTIFIER = "[" + id_start + "]+[" + id_continue + "]*";
const IS_IDENTIFIER_REGEX = new RegExp("^" + IDENTIFIER + "$");

/**
 * test if string is an identifier
 *
 * @param {str} string
 * @returns {boolean}
 */
function isidentifier(str) {
    var normalized = str.normalize("NFKC");
    return IS_IDENTIFIER_REGEX.test(normalized);
}

module.exports = { IDENTIFIER, isIdentifier: isidentifier };

