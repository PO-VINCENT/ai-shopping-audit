// engine.mjs — dependency-free JS port of CatalogReady's deterministic
// product-page readiness audit. Runs identically in Node 22 (parity harness)
// and in a Chrome MV3 extension (browser). Zero Node/DOM APIs: pure
// string/regex/JSON only.
//
// Faithful reimplementation of:
//   optimization/readiness.py      (score_page_readiness)
//   optimization/evidence.py       (evidence_from_html, _ProductHTMLParser)
//   optimization/claims.py         (audit_listing_claims)
//   discovery/scoring.py           (audit_page_html)
//   discovery/structured_data.py   (audit_product_structured_data)
//   discovery/quality.py           (audit_page_quality)
//   discovery/canonical.py         (audit_canonical)
//   discovery/content_evidence.py  (PageSignals, evidence_coverage)
//   catalog/{identifiers,metrics,platforms,schemas}.py
//   agent/{tools,orchestrator}.py  (build_agent_findings display list + dedup)

import { HTML5_ENTITIES } from "./entities.mjs";

/* =========================================================================
 * html.unescape — faithful port of CPython html/__init__.py unescape()
 * ========================================================================= */

const _INVALID_CHARREFS = {
  0x00: "�", 0x0d: "\r", 0x80: "€", 0x81: "\x81", 0x82: "‚",
  0x83: "ƒ", 0x84: "„", 0x85: "…", 0x86: "†", 0x87: "‡",
  0x88: "ˆ", 0x89: "‰", 0x8a: "Š", 0x8b: "‹", 0x8c: "Œ",
  0x8d: "\x8d", 0x8e: "Ž", 0x8f: "\x8f", 0x90: "\x90", 0x91: "‘",
  0x92: "’", 0x93: "“", 0x94: "”", 0x95: "•", 0x96: "–",
  0x97: "—", 0x98: "˜", 0x99: "™", 0x9a: "š", 0x9b: "›",
  0x9c: "œ", 0x9d: "\x9d", 0x9e: "ž", 0x9f: "Ÿ",
};

const _INVALID_CODEPOINTS = new Set([
  0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7, 0x8, 0xe, 0xf, 0x10, 0x11, 0x12, 0x13,
  0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1a, 0x1b, 0x1c, 0x1d, 0x1e, 0x1f, 0x7f,
  0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8a, 0x8b, 0x8c,
  0x8d, 0x8e, 0x8f, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99,
  0x9a, 0x9b, 0x9c, 0x9d, 0x9e, 0x9f, 0xfdd0, 0xfdd1, 0xfdd2, 0xfdd3, 0xfdd4,
  0xfdd5, 0xfdd6, 0xfdd7, 0xfdd8, 0xfdd9, 0xfdda, 0xfddb, 0xfddc, 0xfddd,
  0xfdde, 0xfddf, 0xfde0, 0xfde1, 0xfde2, 0xfde3, 0xfde4, 0xfde5, 0xfde6,
  0xfde7, 0xfde8, 0xfde9, 0xfdea, 0xfdeb, 0xfdec, 0xfded, 0xfdee, 0xfdef, 0xb,
  0xfffe, 0xffff, 0x1fffe, 0x1ffff, 0x2fffe, 0x2ffff, 0x3fffe, 0x3ffff,
  0x4fffe, 0x4ffff, 0x5fffe, 0x5ffff, 0x6fffe, 0x6ffff, 0x7fffe, 0x7ffff,
  0x8fffe, 0x8ffff, 0x9fffe, 0x9ffff, 0xafffe, 0xaffff, 0xbfffe, 0xbffff,
  0xcfffe, 0xcffff, 0xdfffe, 0xdffff, 0xefffe, 0xeffff, 0xffffe, 0xfffff,
  0x10fffe, 0x10ffff,
]);

// _charref = r'&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)'
const _CHARREF = /&(#[0-9]+;?|#[xX][0-9a-fA-F]+;?|[^\t\n\f <&#;]{1,32};?)/g;

function _rstripSemi(s) {
  return s.endsWith(";") ? s.slice(0, -1) : s;
}

function _replaceCharref(_m, s) {
  if (s[0] === "#") {
    let num;
    if (s[1] === "x" || s[1] === "X") num = parseInt(_rstripSemi(s.slice(2)), 16);
    else num = parseInt(_rstripSemi(s.slice(1)), 10);
    if (num in _INVALID_CHARREFS) return _INVALID_CHARREFS[num];
    if ((num >= 0xd800 && num <= 0xdfff) || num > 0x10ffff) return "�";
    if (_INVALID_CODEPOINTS.has(num)) return "";
    return String.fromCodePoint(num);
  }
  // named charref
  if (Object.prototype.hasOwnProperty.call(HTML5_ENTITIES, s)) return HTML5_ENTITIES[s];
  for (let x = s.length - 1; x > 1; x--) {
    const pre = s.slice(0, x);
    if (Object.prototype.hasOwnProperty.call(HTML5_ENTITIES, pre)) {
      return HTML5_ENTITIES[pre] + s.slice(x);
    }
  }
  return "&" + s;
}

function unescape(s) {
  if (s.indexOf("&") === -1) return s;
  return s.replace(_CHARREF, _replaceCharref);
}

/* =========================================================================
 * HTMLParser — faithful port of CPython 3.11 html/parser.py goahead()
 *   convert_charrefs=True; feed()-only (close() is never called upstream).
 * ========================================================================= */

const CDATA_CONTENT_ELEMENTS = new Set(["script", "style", "xmp", "iframe", "noembed", "noframes"]);
const RCDATA_CONTENT_ELEMENTS = new Set(["textarea", "title"]);

// Ported parser regexes (VERBOSE expanded, sticky where matched at a position).
const RE_starttagopen = /<[a-zA-Z]/y;
const RE_endtagopen = /<\/[a-zA-Z]/y;
const RE_locatetagend = /[a-zA-Z][^\t\n\r\f />]*[\t\n\r\f /]*(?:(?<=['"\t\n\r\f /])[^\t\n\r\f />][^\t\n\r\f /=>]*(?:[\t\n\r\f ]*=[\t\n\r\f ]*(?:'[^']*'|"[^"]*"|(?!['"])[^>\t\n\r\f ]*))?[\t\n\r\f /]*)*>?/y;
const RE_tagfind_tolerant = /([a-zA-Z][^\t\n\r\f />]*)(?:[\t\n\r\f ]|\/(?!>))*/y;
const RE_attrfind_tolerant = /((?<=['"\t\n\r\f /])[^\t\n\r\f />][^\t\n\r\f /=>]*)([\t\n\r\f ]*=[\t\n\r\f ]*('[^']*'|"[^"]*"|(?!['"])[^>\t\n\r\f ]*))?(?:[\t\n\r\f ]|\/(?!>))*/y;
const RE_charref = /&#(?:[0-9]+|[xX][0-9a-fA-F]+)[^0-9a-fA-F]/y;
const RE_entityref = /&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]/y;
const RE_incomplete = /&[a-zA-Z#]/y;
const RE_commentclose = /--!?>/g;
const RE_commentabruptclose = /-?>/y;
const RE_piclose = />/g;
const RE_ampstop = /[\t\n\r\f ;]/g;

function stickyMatch(re, s, pos) {
  re.lastIndex = pos;
  return re.exec(s);
}
function searchFrom(re, s, pos) {
  re.lastIndex = pos;
  return re.exec(s);
}

// Python str.strip() default (ASCII whitespace subset used by the parser).
function pyStrip(s) {
  return s.replace(/^[\s]+/, "").replace(/[\s]+$/, "");
}

// Base parser: drives handler callbacks (starttag/startendtag/endtag/data).
// Comment/pi/decl are consumed but not surfaced (subclasses don't use them).
class HTMLParser {
  constructor() {
    this.convert_charrefs = true;
    this.cdata_elem = null;
    this._escapable = true;
    this._interesting = null; // regex source string for cdata closing tag
  }

  // Overridable
  handle_starttag(_tag, _attrs) {}
  handle_endtag(_tag) {}
  handle_startendtag(tag, attrs) {
    this.handle_starttag(tag, attrs);
    this.handle_endtag(tag);
  }
  handle_data(_data) {}

  set_cdata_mode(elem, escapable) {
    this.cdata_elem = elem.toLowerCase();
    this._escapable = escapable;
    // convert_charrefs is always true here → interesting is the closing tag.
    this._interesting = new RegExp("</" + this.cdata_elem + "(?=[\\t\\n\\r\\f />])", "gi");
  }
  clear_cdata_mode() {
    this.cdata_elem = null;
    this._escapable = true;
    this._interesting = null;
  }

  feed(data) {
    this.rawdata = data;
    this.goahead(0);
  }

  goahead(end) {
    const rawdata = this.rawdata;
    let i = 0;
    const n = rawdata.length;
    while (i < n) {
      let j;
      if (this.convert_charrefs && !this.cdata_elem) {
        j = rawdata.indexOf("<", i);
        if (j < 0) {
          // Python: amppos = rawdata.rfind('&', max(i, n-34))
          const start = Math.max(i, n - 34);
          const ap = rawdata.lastIndexOf("&");
          const amppos = ap >= start ? ap : -1;
          if (amppos >= 0 && !searchFrom(RE_ampstop, rawdata, amppos)) break;
          j = n;
        }
      } else {
        const match = searchFrom(this._interesting, rawdata, i);
        if (match) j = match.index;
        else {
          if (this.cdata_elem) break;
          j = n;
        }
      }
      if (i < j) {
        if (this.convert_charrefs && this._escapable) this.handle_data(unescape(rawdata.slice(i, j)));
        else this.handle_data(rawdata.slice(i, j));
      }
      i = j;
      if (i === n) break;
      if (rawdata[i] === "<") {
        let k;
        if (stickyMatch(RE_starttagopen, rawdata, i)) k = this.parse_starttag(i);
        else if (rawdata.startsWith("</", i)) k = this.parse_endtag(i);
        else if (rawdata.startsWith("<!--", i)) k = this.parse_comment(i);
        else if (rawdata.startsWith("<?", i)) k = this.parse_pi(i);
        else if (rawdata.startsWith("<!", i)) k = this.parse_html_declaration(i);
        else if (i + 1 < n || end) {
          this.handle_data("<");
          k = i + 1;
        } else break;
        if (k < 0) {
          if (!end) break;
          k = n; // (end-branch simplification; close() is never called upstream)
        }
        i = k;
      } else if (rawdata.startsWith("&#", i)) {
        const m = stickyMatch(RE_charref, rawdata, i);
        if (m) {
          let k = i + m[0].length;
          if (rawdata[k - 1] !== ";") k = k - 1;
          i = k;
          continue;
        } else {
          if (rawdata.indexOf(";", i) !== -1) {
            this.handle_data(rawdata.slice(i, i + 2));
            i = i + 2;
          }
          break;
        }
      } else if (rawdata[i] === "&") {
        const m = stickyMatch(RE_entityref, rawdata, i);
        if (m) {
          let k = i + m[0].length;
          if (rawdata[k - 1] !== ";") k = k - 1;
          i = k;
          continue;
        }
        const mi = stickyMatch(RE_incomplete, rawdata, i);
        if (mi) break;
        else if (i + 1 < n) {
          this.handle_data("&");
          i = i + 1;
        } else break;
      } else {
        break;
      }
    }
    this.rawdata = rawdata.slice(i);
  }

  check_for_whole_start_tag(i) {
    const rawdata = this.rawdata;
    const match = stickyMatch(RE_locatetagend, rawdata, i + 1);
    const j = i + 1 + match[0].length;
    if (rawdata[j - 1] !== ">") return -1;
    return j;
  }

  parse_starttag(i) {
    const rawdata = this.rawdata;
    const endpos = this.check_for_whole_start_tag(i);
    if (endpos < 0) return endpos;
    const attrs = [];
    const tm = stickyMatch(RE_tagfind_tolerant, rawdata, i + 1);
    let k = i + 1 + tm[0].length;
    const tag = tm[1].toLowerCase();
    while (k < endpos) {
      const m = stickyMatch(RE_attrfind_tolerant, rawdata, k);
      if (!m || m.index !== k || m[0].length === 0) break;
      let attrname = m[1];
      const rest = m[2];
      let attrvalue = m[3];
      if (!rest) attrvalue = null;
      else if (
        (attrvalue[0] === "'" && attrvalue[attrvalue.length - 1] === "'") ||
        (attrvalue[0] === '"' && attrvalue[attrvalue.length - 1] === '"')
      ) {
        attrvalue = attrvalue.slice(1, -1);
      }
      if (attrvalue) attrvalue = unescape(attrvalue);
      attrs.push([attrname.toLowerCase(), attrvalue]);
      k = k + m[0].length;
    }
    const endStr = pyStrip(rawdata.slice(k, endpos));
    if (endStr !== ">" && endStr !== "/>") {
      this.handle_data(rawdata.slice(i, endpos));
      return endpos;
    }
    if (endStr.endsWith("/>")) {
      this.handle_startendtag(tag, attrs);
    } else {
      this.handle_starttag(tag, attrs);
      if (CDATA_CONTENT_ELEMENTS.has(tag) || tag === "plaintext") this.set_cdata_mode(tag, false);
      else if (RCDATA_CONTENT_ELEMENTS.has(tag)) this.set_cdata_mode(tag, true);
    }
    return endpos;
  }

  parse_endtag(i) {
    const rawdata = this.rawdata;
    if (rawdata.indexOf(">", i + 2) < 0) return -1;
    if (!stickyMatch(RE_endtagopen, rawdata, i)) {
      if (rawdata.slice(i + 2, i + 3) === ">") return i + 3;
      return this.parse_bogus_comment(i);
    }
    const match = stickyMatch(RE_locatetagend, rawdata, i + 2);
    const j = i + 2 + match[0].length;
    if (rawdata[j - 1] !== ">") return -1;
    const tm = stickyMatch(RE_tagfind_tolerant, rawdata, i + 2);
    const tag = tm[1].toLowerCase();
    this.handle_endtag(tag);
    this.clear_cdata_mode();
    return j;
  }

  parse_comment(i) {
    const rawdata = this.rawdata;
    let match = searchFrom(RE_commentclose, rawdata, i + 4);
    if (!match) {
      match = stickyMatch(RE_commentabruptclose, rawdata, i + 4);
      if (!match) return -1;
      return i + 4 + match[0].length;
    }
    return match.index + match[0].length;
  }

  parse_bogus_comment(i) {
    const rawdata = this.rawdata;
    const pos = rawdata.indexOf(">", i + 2);
    if (pos === -1) return -1;
    return pos + 1;
  }

  parse_pi(i) {
    const rawdata = this.rawdata;
    const match = searchFrom(RE_piclose, rawdata, i + 2);
    if (!match) return -1;
    return match.index + match[0].length;
  }

  parse_html_declaration(i) {
    const rawdata = this.rawdata;
    if (rawdata.slice(i, i + 4) === "<!--") return this.parse_comment(i);
    if (rawdata.slice(i, i + 9) === "<![CDATA[") {
      const j = rawdata.indexOf("]]>", i + 9);
      if (j < 0) return -1;
      return j + 3;
    }
    if (rawdata.slice(i, i + 9).toLowerCase() === "<!doctype") {
      const gtpos = rawdata.indexOf(">", i + 9);
      if (gtpos === -1) return -1;
      return gtpos + 1;
    }
    if (rawdata.slice(i, i + 3) === "<![") {
      const j = rawdata.indexOf(">", i + 3);
      if (j < 0) return -1;
      return j + 1;
    }
    return this.parse_bogus_comment(i);
  }
}

/* =========================================================================
 * optimization/evidence.py :: _ProductHTMLParser
 * ========================================================================= */

const _BLOCK_TAGS = new Set([
  "address", "article", "aside", "blockquote", "br", "dd", "div", "dl", "dt",
  "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4",
  "h5", "h6", "header", "hr", "li", "main", "nav", "ol", "p", "section",
  "table", "td", "th", "tr", "ul",
]);

function attrValues(attrs) {
  const values = {};
  for (const [key, value] of attrs) values[key.toLowerCase()] = value || "";
  return values;
}

// " ".join(data.split()) — collapse all whitespace runs, trim.
function joinSplit(data) {
  return data.split(/\s+/).filter((x) => x.length > 0).join(" ");
}

class ProductHTMLParser extends HTMLParser {
  constructor() {
    super();
    this.title = "";
    this._in_title = false;
    this._in_jsonld = false;
    this._ignored_depth = 0;
    this._script_parts = [];
    this.jsonld = [];
    this.meta = {};
    this.canonical = "";
    this._text_parts = [];
  }
  _block_boundary() {
    if (this._text_parts.length && this._text_parts[this._text_parts.length - 1] !== "\n") {
      this._text_parts.push("\n");
    }
  }
  handle_starttag(tag, attrs) {
    const values = attrValues(attrs);
    const lowered = tag.toLowerCase();
    if (lowered === "title") this._in_title = true;
    else if (lowered === "script" && (values["type"] || "").toLowerCase() === "application/ld+json") {
      this._in_jsonld = true;
      this._script_parts = [];
    } else if (lowered === "script" || lowered === "style" || lowered === "noscript") {
      this._ignored_depth += 1;
    } else if (lowered === "meta") {
      const key = values["property"] || values["name"] || values["itemprop"];
      if (key && values["content"]) this.meta[key.toLowerCase()] = values["content"];
    } else if (lowered === "link" && (values["rel"] || "").toLowerCase() === "canonical") {
      this.canonical = values["href"] || "";
    }
    if (_BLOCK_TAGS.has(lowered)) this._block_boundary();
  }
  handle_endtag(tag) {
    const lowered = tag.toLowerCase();
    if (lowered === "title") this._in_title = false;
    else if (lowered === "script" && this._in_jsonld) {
      this._in_jsonld = false;
      const raw = this._script_parts.join("").trim();
      if (raw) {
        try {
          this.jsonld.push(JSON.parse(raw));
        } catch (e) {
          /* pass */
        }
      }
    } else if ((lowered === "script" || lowered === "style" || lowered === "noscript") && this._ignored_depth) {
      this._ignored_depth -= 1;
    }
    if (_BLOCK_TAGS.has(lowered)) this._block_boundary();
  }
  handle_data(data) {
    if (this._in_title) this.title += data;
    if (this._in_jsonld) {
      this._script_parts.push(data);
      return;
    }
    if (this._ignored_depth) return;
    const cleaned = joinSplit(data);
    if (cleaned) this._text_parts.push(cleaned);
  }
  get visible_text() {
    const joined = this._text_parts.join(" ");
    return joined.replace(/\s*\n\s*/g, "\n").replace(/^\s+/, "").replace(/\s+$/, "");
  }
}

/* =========================================================================
 * discovery/content_evidence.py :: PageSignals
 * ========================================================================= */

class PageSignals extends HTMLParser {
  constructor() {
    super();
    this.in_title = false;
    this.ignored_depth = 0;
    this.json_ld_depth = 0;
    this.title_parts = [];
    this.text_parts = [];
    this.json_ld_blocks = [];
    this._json_ld_parts = [];
    this.canonical = null;
    this.robots = "";
    this.description = "";
    this.lang = "";
    this.links = [];
    this._link_href = null;
    this._link_text = [];
  }
  handle_starttag(tag, attrs) {
    const values = attrValues(attrs);
    const lowered = tag.toLowerCase();
    if (lowered === "html") this.lang = (values["lang"] || "").trim();
    if (lowered === "title") this.in_title = true;
    else if (lowered === "style" || lowered === "noscript") this.ignored_depth += 1;
    else if (lowered === "script") {
      if ((values["type"] || "").toLowerCase() === "application/ld+json") {
        this.json_ld_depth += 1;
        this._json_ld_parts = [];
      } else this.ignored_depth += 1;
    } else if (lowered === "link" && (values["rel"] || "").toLowerCase().split(/\s+/).includes("canonical")) {
      this.canonical = values["href"] || null;
    } else if (lowered === "meta" && (values["name"] || "").toLowerCase() === "robots") {
      this.robots = (values["content"] || "").toLowerCase();
    } else if (lowered === "meta" && (values["name"] || "").toLowerCase() === "description") {
      this.description = (values["content"] || "").trim();
    } else if (lowered === "a") {
      this._link_href = values["href"] || "";
      this._link_text = [];
    }
  }
  handle_endtag(tag) {
    const lowered = tag.toLowerCase();
    if (lowered === "a" && this._link_href !== null) {
      this.links.push([this._link_href, this._link_text.join(" ").trim().toLowerCase()]);
      this._link_href = null;
      this._link_text = [];
    }
    if (lowered === "title") this.in_title = false;
    else if ((lowered === "style" || lowered === "noscript") && this.ignored_depth) this.ignored_depth -= 1;
    else if (lowered === "script") {
      if (this.json_ld_depth) {
        const block = this._json_ld_parts.join("").trim();
        if (block) this.json_ld_blocks.push(block);
        this.json_ld_depth -= 1;
        this._json_ld_parts = [];
      } else if (this.ignored_depth) this.ignored_depth -= 1;
    }
  }
  handle_data(data) {
    if (this.json_ld_depth) {
      this._json_ld_parts.push(data);
      return;
    }
    if (this.ignored_depth) return;
    const cleaned = joinSplit(data);
    if (!cleaned) return;
    if (this.in_title) this.title_parts.push(cleaned);
    if (this._link_href !== null) this._link_text.push(cleaned);
    this.text_parts.push(cleaned);
  }
  get title() {
    return this.title_parts.join(" ").trim();
  }
  get visible_text() {
    return this.text_parts.join(" ");
  }
  get visible_words() {
    return this.visible_text.split(/\s+/).filter((x) => x.length > 0).length;
  }
}

/* =========================================================================
 * evidence.py helpers
 * ========================================================================= */

function pyStr(value) {
  // Mimic Python str() for the JSON-scalar types we encounter.
  if (value === true) return "True";
  if (value === false) return "False";
  if (value === null) return "None";
  return String(value);
}

function _clean(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) {
    value = value.map((item) => _clean(item)).filter((item) => item).join(", ");
  } else if (typeof value === "object") {
    value = value.name || value.value || value.url || "";
  }
  let text = unescape(pyStr(value));
  text = text.replace(/<[^>]+>/g, " ");
  return text.replace(/\s+/g, " ").trim();
}

function _first(...values) {
  for (const value of values) {
    const cleaned = _clean(value);
    if (cleaned) return cleaned;
  }
  return "";
}

function _availability(value) {
  const text = _clean(value).toLowerCase().split("/").pop();
  const aliases = {
    instock: "in_stock", "in stock": "in_stock", in_stock: "in_stock",
    outofstock: "out_of_stock", "out of stock": "out_of_stock", out_of_stock: "out_of_stock",
    preorder: "preorder", pre_order: "preorder", backorder: "backorder", back_order: "backorder",
  };
  return Object.prototype.hasOwnProperty.call(aliases, text) ? aliases[text] : text;
}

function _price(value, currency = "") {
  const text = _clean(value);
  const amountMatch = text.match(/-?\d+(?:[.,]\d+)?/);
  const amount = amountMatch ? amountMatch[0].replace(/,/g, ".") : "";
  let resolvedCurrency = _clean(currency).toUpperCase();
  if (!resolvedCurrency) {
    const currencyMatch = text.toUpperCase().match(/\b[A-Z]{3}\b/);
    if (currencyMatch) resolvedCurrency = currencyMatch[0];
  }
  return { amount, currency: resolvedCurrency };
}

function _images(value) {
  const values = Array.isArray(value) ? value : [value];
  const result = [];
  for (const item of values) {
    const url = _clean(item);
    if (url && !result.includes(url)) result.push(url);
  }
  return result;
}

function _specifications(product) {
  const specs = [];
  let properties = product.additionalProperty || [];
  if (properties && !Array.isArray(properties) && typeof properties === "object") properties = [properties];
  if (!Array.isArray(properties)) properties = [];
  for (const item of properties) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    const name = _first(item.name, item.propertyID);
    const value = _first(item.value, item.valueReference);
    if (name && value) specs.push({ name, value });
  }
  for (const field of ["color", "material", "size", "pattern", "weight"]) {
    const value = _clean(product[field]);
    if (value && !specs.some((spec) => spec.name.toLowerCase() === field)) {
      specs.push({ name: field, value });
    }
  }
  return specs;
}

// evidence.py :: _walk_jsonld
function _walk_jsonld(value) {
  const found = [];
  if (Array.isArray(value)) {
    for (const item of value) found.push(..._walk_jsonld(item));
  } else if (value && typeof value === "object") {
    found.push(value);
    if ("@graph" in value) found.push(..._walk_jsonld(value["@graph"]));
  }
  return found;
}

function _product_jsonld(parser) {
  for (const block of parser.jsonld) {
    for (const node of _walk_jsonld(block)) {
      let types = node["@type"] || [];
      if (typeof types === "string") types = [types];
      if (Array.isArray(types) && types.some((item) => pyStr(item).toLowerCase() === "product")) return node;
    }
  }
  return {};
}

function _offer(product) {
  let offers = product.offers || {};
  if (Array.isArray(offers)) offers = offers.length ? offers[0] : {};
  return offers && typeof offers === "object" && !Array.isArray(offers) ? offers : {};
}

/* --- page_topic_evidence & specifications_from_text --- */

const _PAGE_TOPICS = [
  ["shipping", ["shipping", "delivery", "dispatch", "ships "]],
  ["returns", ["return", "refund", "exchange"]],
  ["warranty", ["warranty", "guarantee"]],
  ["care", ["care instructions", "machine wash", "hand wash", "wipe clean", "do not bleach"]],
  ["materials", ["material", "made from", "made of", "recycled", "fabric"]],
  ["limitations", ["not suitable", "not intended", "avoid", "warning", "limitation"]],
];

function page_topic_evidence(visibleText) {
  const sentences = [];
  for (const block of visibleText.split("\n")) {
    for (let sentence of block.split(/(?<=[.!?])\s+/)) {
      sentence = sentence.trim();
      if (sentence.length >= 30) sentences.push(sentence);
    }
  }
  const topics = {};
  for (const [topic, keywords] of _PAGE_TOPICS) {
    for (const sentence of sentences) {
      const lowered = sentence.toLowerCase();
      if (keywords.some((keyword) => lowered.includes(keyword))) {
        topics[topic] = sentence.slice(0, 240);
        break;
      }
    }
  }
  return topics;
}

const _SPEC_KEY_STOPLIST = new Set(["http", "https", "note", "important", "warning", "tip", "example", "faq", "q", "a", "step"]);
const _SPEC_KEY_PATTERN = /\b([A-Za-z][A-Za-z()'&.-]+(?:\s+[A-Za-z][A-Za-z()'&.-]+){0,3})\s*:\s*/g;

function pyStripChars(s, chars) {
  let start = 0;
  let end = s.length;
  while (start < end && chars.includes(s[start])) start++;
  while (end > start && chars.includes(s[end - 1])) end--;
  return s.slice(start, end);
}

function specifications_from_text(visibleText, limit = 20) {
  const flattened = visibleText.replace(/\n/g, " ");
  const anchor = flattened.match(/specifications?\s*:?/i);
  if (!anchor) return [];
  let region = flattened.slice(anchor.index + anchor[0].length);
  const stop = region.match(/package content|warranty|returns policy|delivery/i);
  if (stop && stop.index > 0) region = region.slice(0, stop.index);
  region = region.slice(0, 1500);

  const matches = [];
  _SPEC_KEY_PATTERN.lastIndex = 0;
  let m;
  while ((m = _SPEC_KEY_PATTERN.exec(region)) !== null) {
    matches.push({ index: m.index, end: m.index + m[0].length, g1: m[1] });
    if (m[0].length === 0) _SPEC_KEY_PATTERN.lastIndex++;
  }
  const specs = [];
  const seen = new Set();
  for (let index = 0; index < matches.length; index++) {
    const match = matches[index];
    const key = pyStripChars(joinSplit(match.g1), "-. ");
    const end = index + 1 < matches.length ? matches[index + 1].index : region.length;
    const value = pyStripChars(region.slice(match.end, end), " ;,.");
    if (!key || !value || value.length > 80) continue;
    if (_SPEC_KEY_STOPLIST.has(key.toLowerCase()) || seen.has(key.toLowerCase())) continue;
    seen.add(key.toLowerCase());
    specs.push({ name: key, value });
    if (specs.length >= limit) break;
  }
  return specs;
}

function _now() {
  return new Date().toISOString().replace(/\.\d+Z$/, "+00:00").replace("Z", "+00:00");
}

function _evidence_record(source, product) {
  const evidence = [];
  const add = (evidenceId, field, value) => {
    const cleaned = _clean(value);
    if (cleaned) evidence.push({ id: evidenceId, field, value: cleaned, source: source.uri || source.kind });
  };
  for (const field of ["id", "title", "description", "category", "brand", "sku", "gtin", "mpn", "url"]) {
    add(`product.${field}`, field, product[field]);
  }
  const price = product.price || {};
  add("offer.price", "price", price.amount);
  add("offer.currency", "currency", price.currency);
  add("offer.availability", "availability", product.availability);
  (product.images || []).forEach((image, idx) => add(`image.${idx + 1}`, "image", image));
  (product.specifications || []).forEach((spec, idx) => add(`spec.${idx + 1}`, `specification.${spec.name || ""}`, spec.value));
  const review = product.review_summary || {};
  add("review.rating", "aggregate_rating", review.rating);
  add("review.count", "review_count", review.count);
  return { schema_version: "1.0", source, product, evidence };
}

function evidence_from_html(url, html) {
  if (!url.trim()) throw new Error("url is required");
  if (!html.trim()) throw new Error("html is required");
  const parser = new ProductHTMLParser();
  parser.feed(html);
  const node = _product_jsonld(parser);
  const offer = _offer(node);
  const brand = node.brand || {};
  const aggregate = node.aggregateRating || {};
  const product = {
    id: _first(node.productID, node.sku, parser.meta["product:retailer_item_id"]),
    title: _first(node.name, parser.meta["og:title"], parser.title),
    description: _first(node.description, parser.meta["og:description"], parser.meta["description"]),
    category: _first(node.category, parser.meta["product:category"]),
    brand: _first(brand, node.manufacturer),
    sku: _clean(node.sku),
    gtin: _first(node.gtin, node.gtin13, node.gtin12, node.gtin14),
    mpn: _clean(node.mpn),
    url: _first(node.url, parser.canonical, parser.meta["og:url"], url),
    images: _images(node.image || parser.meta["og:image"]),
    price: _price(
      offer.price || offer.lowPrice || parser.meta["product:price:amount"],
      offer.priceCurrency || parser.meta["product:price:currency"]
    ),
    availability: _availability(offer.availability || parser.meta["product:availability"]),
    review_summary: {
      rating: _clean(aggregate.ratingValue),
      count: _first(aggregate.reviewCount, aggregate.ratingCount),
    },
  };
  const fromNode = _specifications(node);
  product.specifications = fromNode.length ? fromNode : specifications_from_text(parser.visible_text);
  const record = _evidence_record({ kind: "url_html", uri: url, observed_at: _now() }, product);
  const topics = page_topic_evidence(parser.visible_text);
  for (const topic of Object.keys(topics)) {
    record.evidence.push({ id: `page.${topic}`, field: `page_evidence.${topic}`, value: topics[topic], source: url });
  }
  return record;
}

/* =========================================================================
 * catalog/identifiers.py :: is_valid_gtin
 * ========================================================================= */

const GTIN_LENGTHS = new Set([8, 12, 13, 14]);
function is_valid_gtin(value) {
  const digits = pyStr(value == null ? "" : value).trim();
  if (!/^\d+$/.test(digits) || !GTIN_LENGTHS.has(digits.length)) return false;
  let total = 0;
  const body = digits.slice(0, -1);
  const reversed = body.split("").reverse();
  for (let position = 0; position < reversed.length; position++) {
    const weight = position % 2 === 0 ? 3 : 1;
    total += parseInt(reversed[position], 10) * weight;
  }
  return ((10 - (total % 10)) % 10) === parseInt(digits[digits.length - 1], 10);
}

/* =========================================================================
 * catalog/metrics.py :: metric_for
 * ========================================================================= */

const METRICS = [
  "machine_readability", "validity", "completeness", "consistency", "trust",
  "accessibility", "transactability", "freshness",
];

const _METRIC_EXACT = {
  "GEO-PRODUCT-001": "machine_readability", "GEO-PRODUCT-002": "machine_readability",
  "SEO-JSONLD-001": "machine_readability", "SEO-LANG-001": "machine_readability",
  "GEO-EVIDENCE-001": "machine_readability", "GEO-GTIN-001": "validity",
  "GEO-CURRENCY-001": "validity", "GEO-AVAILABILITY-002": "validity", "GEO-OFFER-002": "validity",
  "GEO-EVIDENCE-002": "completeness", "GEO-RETURNS-001": "completeness",
  "GEO-SHIPPING-001": "completeness", "GEO-RATING-001": "completeness",
  "GEO-PRODUCT-003": "consistency", "GEO-OFFER-003": "consistency", "CAT-IDENTITY-001": "consistency",
  "CAT-VARIANT-003": "consistency", "CAT-VARIANT-004": "consistency", "CAT-TAXONOMY-001": "consistency",
  "SEO-TITLE-002": "trust", "SEO-ROBOTS-001": "accessibility", "SEO-SNIPPET-001": "accessibility",
  "SEO-CANONICAL-001": "accessibility", "SEO-CANONICAL-002": "accessibility", "SEO-CANONICAL-003": "accessibility",
  "SEO-SITEMAP-001": "accessibility", "SEO-SITEMAP-002": "accessibility", "SEO-TITLE-001": "accessibility",
  "SEO-DESC-001": "accessibility", "SEO-HTTPS-001": "accessibility", "GEO-IMAGE-001": "accessibility",
  "GEO-IMAGE-002": "accessibility", "GEO-POLICY-001": "transactability", "GEO-SELLER-001": "transactability",
  "GEO-RETURNS-002": "transactability", "GEO-SHIPPING-002": "transactability", "GEO-CONDITION-001": "transactability",
  "GEO-PRODUCT-004": "transactability", "GEO-VARIANT-001": "transactability",
  "GEO-OFFER-004": "freshness", "SEO-INDEXNOW-001": "freshness",
};
const _METRIC_PREFIX = [
  ["CAT-COLUMN-", "completeness"], ["CAT-VALUE-", "completeness"], ["CAT-ATTR-", "completeness"],
  ["SEO-ROBOTS-", "accessibility"], ["AGENT-", "completeness"], ["CLAIM-", "trust"],
];
const _METRIC_FAMILY = { CAT: "consistency", SEO: "accessibility", GEO: "machine_readability" };

function metric_for(ruleId) {
  ruleId = String(ruleId || "");
  if (ruleId in _METRIC_EXACT) return _METRIC_EXACT[ruleId];
  for (const [prefix, metric] of _METRIC_PREFIX) if (ruleId.startsWith(prefix)) return metric;
  const fam = ruleId.split("-", 1)[0];
  return Object.prototype.hasOwnProperty.call(_METRIC_FAMILY, fam) ? _METRIC_FAMILY[fam] : "machine_readability";
}

/* =========================================================================
 * catalog/platforms.py
 * ========================================================================= */

const PLATFORMS = ["openai", "google", "microsoft", "anthropic", "perplexity"];
const PLATFORM_LABELS = {
  openai: "OpenAI", google: "Google", microsoft: "Microsoft Bing",
  anthropic: "Anthropic", perplexity: "Perplexity",
};
const PLATFORM_SURFACES = {
  openai: ["ChatGPT search", "ChatGPT shopping"],
  google: ["Merchant listings", "Google Shopping", "AI Overviews", "AI Mode"],
  microsoft: ["Bing search", "Microsoft Shopping", "Copilot"],
  anthropic: ["Claude"],
  perplexity: ["Perplexity"],
};
const _MARKUP = ["google", "microsoft"];
const _PLATFORM_EXACT = {
  "SEO-ROBOTS-GOOGLEBOT": ["google"], "SEO-ROBOTS-BINGBOT": ["microsoft"],
  "SEO-ROBOTS-OAI_SEARCHBOT": ["openai"], "SEO-ROBOTS-PERPLEXITYBOT": ["perplexity"],
  "SEO-ROBOTS-CLAUDE_SEARCHBOT": ["anthropic"], "SEO-SNIPPET-001": ["google", "microsoft"],
  "SEO-SITEMAP-001": _MARKUP, "SEO-SITEMAP-002": _MARKUP, "GEO-PRODUCT-001": _MARKUP,
  "GEO-PRODUCT-002": _MARKUP, "GEO-PRODUCT-004": _MARKUP, "SEO-JSONLD-001": _MARKUP,
  "GEO-OFFER-001": _MARKUP, "GEO-OFFER-003": _MARKUP, "GEO-OFFER-004": _MARKUP,
  "GEO-CURRENCY-001": _MARKUP, "GEO-AVAILABILITY-002": _MARKUP, "GEO-VARIANT-001": _MARKUP,
  "GEO-RETURNS-002": ["google"], "GEO-SHIPPING-002": ["google"],
  "GEO-GTIN-001": ["google", "microsoft", "openai"], "GEO-CONDITION-001": ["google", "microsoft", "openai"],
  "GEO-RATING-001": ["google", "microsoft", "openai"], "GEO-POLICY-001": ["openai", "google", "microsoft"],
  "GEO-SELLER-001": ["openai", "google", "microsoft", "perplexity"],
  "GEO-SHIPPING-001": ["openai", "google", "microsoft", "perplexity"],
};
function platforms_for(ruleId) {
  return _PLATFORM_EXACT[String(ruleId || "")] || PLATFORMS;
}

/* =========================================================================
 * catalog/schemas.py :: finding
 * ========================================================================= */

function finding(ruleId, severity, title, evidence, recommendation, source = "deterministic_rule") {
  return {
    rule_id: ruleId, severity, title, evidence, recommendation, source,
    metric: metric_for(ruleId), platforms: [...platforms_for(ruleId)],
  };
}
function percent(passed, total) {
  if (total <= 0) return 0;
  // Python round() uses banker's rounding; replicate.
  return bankersRound((100 * passed) / total);
}
function bankersRound(x) {
  const floor = Math.floor(x);
  const diff = x - floor;
  if (diff < 0.5) return floor;
  if (diff > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
}

/* =========================================================================
 * discovery/structured_data.py
 * ========================================================================= */

const _ISO_4217 = new Set([
  "AED", "ARS", "AUD", "BGN", "BHD", "BRL", "CAD", "CHF", "CLP", "CNY", "COP",
  "CZK", "DKK", "EGP", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY",
  "KRW", "KWD", "MAD", "MXN", "MYR", "NGN", "NOK", "NZD", "PEN", "PHP", "PKR",
  "PLN", "QAR", "RON", "RSD", "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "UAH",
  "USD", "VND", "ZAR",
]);
const _AVAILABILITY_VOCAB = new Set([
  "instock", "outofstock", "preorder", "presale", "backorder", "discontinued",
  "limitedavailability", "instoreonly", "onlineonly", "soldout", "madetoorder", "reserved",
]);
const _GTIN_KEYS = ["gtin", "gtin8", "gtin12", "gtin13", "gtin14"];

// structured_data.py :: _nodes
function _sd_nodes(value) {
  const out = [];
  if (Array.isArray(value)) {
    for (const item of value) out.push(..._sd_nodes(item));
  } else if (value && typeof value === "object") {
    out.push(value);
    const graph = value["@graph"];
    if (graph !== undefined && graph !== null) out.push(..._sd_nodes(graph));
  }
  return out;
}

function parse_json_ld(blocks) {
  const nodes = [];
  let invalid = 0;
  for (const block of blocks) {
    let parsed;
    try {
      parsed = JSON.parse(block);
    } catch (e) {
      invalid += 1;
      continue;
    }
    nodes.push(..._sd_nodes(parsed));
  }
  return { nodes, invalid };
}

function _has_type(node, expected) {
  const nodeType = node["@type"];
  if (Array.isArray(nodeType)) return nodeType.includes(expected);
  return nodeType === expected;
}

function _price_value(offer) {
  let raw = offer.price;
  if (raw && typeof raw === "object" && !Array.isArray(raw)) raw = raw.price;
  const f = parseFloat(pyStr(raw == null ? "None" : raw).replace(/,/g, ""));
  if (Number.isNaN(f)) return null;
  // Python float(str(raw)) fails for e.g. "1 2"; parseFloat is lenient. Guard:
  const s = pyStr(raw == null ? "None" : raw).replace(/,/g, "").trim();
  if (!/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s)) return null;
  return f;
}

function todayParts() {
  const d = new Date();
  return { y: d.getFullYear(), m: d.getMonth() + 1, day: d.getDate() };
}

function audit_product_structured_data(blocks) {
  const { nodes, invalid } = parse_json_ld(blocks);
  const products = nodes.filter((node) => _has_type(node, "Product"));
  const offers = nodes.filter((node) => _has_type(node, "Offer"));
  for (const product of products) {
    const po = product.offers;
    if (po && typeof po === "object" && !Array.isArray(po)) offers.push(po);
    else if (Array.isArray(po)) for (const item of po) if (item && typeof item === "object" && !Array.isArray(item)) offers.push(item);
  }

  const findings = [];
  if (invalid) {
    findings.push(finding("SEO-JSONLD-001", "medium", "Invalid JSON-LD blocks",
      `${invalid} JSON-LD blocks could not be parsed.`,
      "Emit valid JSON and test the rendered page before publishing."));
  }
  if (!products.length) {
    findings.push(finding("GEO-PRODUCT-001", "medium", "Product structured data is missing",
      "No JSON-LD node with @type Product was found.",
      "Add Product data that matches the visible product page."));
  }
  const product_identity = Boolean(products.length && products.every((p) => p.name));
  if (products.length && !product_identity) {
    findings.push(finding("GEO-PRODUCT-002", "medium", "Product structured data lacks a name",
      "At least one Product node has no name.",
      "Use the same verified product name shown to shoppers."));
  }
  const offer_complete = Boolean(
    offers.length && offers.some((offer) => offer.price && offer.priceCurrency && offer.availability)
  );
  if (products.length && !offer_complete) {
    findings.push(finding("GEO-OFFER-001", "medium", "Offer data is incomplete",
      "No offer includes price, currency, and availability together.",
      "Align Offer fields with the visible price and availability."));
  }

  const priced = offers.map((o) => _price_value(o)).filter((v) => v !== null);
  if (priced.length && Math.max(...priced) <= 0) {
    findings.push(finding("GEO-OFFER-002", "high", "Offer price is not greater than zero",
      `The highest machine-readable offer price is ${pyFloatRepr(Math.max(...priced))}.`,
      "Publish the real, current price; merchant listings require a price greater than zero."));
  }

  const bad_gtins = [];
  for (const product of products) {
    for (const key of _GTIN_KEYS) {
      if (product[key] && !is_valid_gtin(pyStr(product[key]))) bad_gtins.push(pyStr(product[key]).trim());
    }
  }
  if (bad_gtins.length) {
    findings.push(finding("GEO-GTIN-001", "high", "GTIN fails GS1 validation",
      `Invalid GTIN value(s): ${bad_gtins.slice(0, 3).join(", ")} (length or check digit).`,
      "Publish the manufacturer-assigned GTIN exactly; an incorrect GTIN is a documented disapproval cause."));
  }

  const bad_currencies = [...new Set(
    offers.filter((o) => o.priceCurrency && !_ISO_4217.has(pyStr(o.priceCurrency).trim().toUpperCase()))
      .map((o) => pyStr(o.priceCurrency).trim())
  )].sort();
  if (bad_currencies.length) {
    findings.push(finding("GEO-CURRENCY-001", "medium", "priceCurrency is not a recognized ISO 4217 code",
      `Unrecognized currency value(s): ${bad_currencies.slice(0, 3).join(", ")}.`,
      "Use a three-letter ISO 4217 code (USD, EUR, AUD, …); agents cannot quote an offer without one."));
  }

  const bad_availability = [...new Set(
    offers.filter((o) => {
      if (!o.availability) return false;
      const tail = pyStr(o.availability).split("/").pop().toLowerCase().replace(/[^a-z]/g, "");
      return !_AVAILABILITY_VOCAB.has(tail);
    }).map((o) => pyStr(o.availability).trim())
  )].sort();
  if (bad_availability.length) {
    findings.push(finding("GEO-AVAILABILITY-002", "medium", "availability is not a schema.org ItemAvailability value",
      `Unrecognized availability value(s): ${bad_availability.slice(0, 3).join(", ")}.`,
      "Use a schema.org value such as https://schema.org/InStock; free-text availability is not machine-readable."));
  }

  const today = todayParts();
  const expired = [];
  for (const offer of offers) {
    const raw = pyStr(offer.priceValidUntil || "").trim();
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!match) continue;
    const y = parseInt(match[1], 10), mo = parseInt(match[2], 10), da = parseInt(match[3], 10);
    if (mo < 1 || mo > 12 || da < 1 || da > 31) continue;
    const before = y < today.y || (y === today.y && (mo < today.m || (mo === today.m && da < today.day)));
    if (before) expired.push(raw);
  }
  if (expired.length) {
    findings.push(finding("GEO-OFFER-004", "medium", "Offer priceValidUntil is in the past",
      `priceValidUntil ${expired.slice(0, 3).join(", ")} has expired.`,
      "Update or remove priceValidUntil; an expired offer date signals stale price data to agents."));
  }

  const return_policies = [];
  for (const node of [...products, ...offers]) {
    let pol = node.hasMerchantReturnPolicy;
    const arr = Array.isArray(pol) ? pol : [pol];
    for (const policy of arr) if (policy && typeof policy === "object" && !Array.isArray(policy)) return_policies.push(policy);
  }
  if (return_policies.length && !return_policies.some((p) => (p.applicableCountry && p.returnPolicyCategory) || p.merchantReturnLink)) {
    findings.push(finding("GEO-RETURNS-002", "medium", "Return-policy markup is incomplete",
      "hasMerchantReturnPolicy declares neither applicableCountry + returnPolicyCategory nor merchantReturnLink.",
      "Complete the MerchantReturnPolicy: applicableCountry + returnPolicyCategory (add merchantReturnDays for finite windows) or a merchantReturnLink URL."));
  }

  const shipping_nodes = offers.map((o) => o.shippingDetails).filter((s) => s && typeof s === "object" && !Array.isArray(s));
  if (shipping_nodes.length && !shipping_nodes.some((s) => s.shippingRate || s.shippingDestination || s.deliveryTime)) {
    findings.push(finding("GEO-SHIPPING-002", "low", "shippingDetails markup carries no shipping facts",
      "OfferShippingDetails declares none of shippingRate, shippingDestination, or deliveryTime.",
      "Populate shippingRate, shippingDestination, and deliveryTime so agents can quote delivery."));
  }

  const has_seller_identity =
    offers.some((o) => o.seller) || nodes.some((n) => _has_type(n, "Organization")) || products.some((p) => p.brand);
  if (products.length && offers.length && !has_seller_identity) {
    findings.push(finding("GEO-SELLER-001", "low", "No machine-readable seller identity",
      "Neither brand, offers.seller, nor an Organization node identifies who sells this product.",
      "Add offers.seller or Organization markup; agentic feeds require seller name and URL."));
  }

  const offered_products = products.filter((p) => p.offers && !p.isVariantOf && !p.inProductGroupWithID);
  if (offered_products.length > 1) {
    const names = offered_products.slice(0, 3).map((p) => pyStr(p.name || "").slice(0, 40));
    findings.push(finding("GEO-PRODUCT-004", "medium", "Multiple ungrouped Product offers on one page",
      `${offered_products.length} Product nodes carry offers without variant grouping (e.g. ${names.join(", ")}).`,
      "Keep one primary Product per page, or link variants with isVariantOf/inProductGroupWithID."));
  }

  return {
    checks: { product: Boolean(products.length), product_identity, offer_complete },
    findings,
    summary: { json_ld_nodes: nodes.length, products: products.length, offers: offers.length, invalid_json_ld: invalid },
    products,
    offers,
  };
}

// Python repr of a float for GEO-OFFER-002 message (unused in scoring parity).
function pyFloatRepr(x) {
  if (Number.isInteger(x)) return x.toFixed(1);
  return String(x);
}

/* =========================================================================
 * discovery/canonical.py
 * ========================================================================= */

function urlsplit(url) {
  // Minimal urllib.parse.urlsplit replica for scheme://netloc/path?query#fragment
  let scheme = "", netloc = "", rest = url, fragment = "", query = "";
  const hashIdx = rest.indexOf("#");
  if (hashIdx >= 0) {
    fragment = rest.slice(hashIdx + 1);
    rest = rest.slice(0, hashIdx);
  }
  const schemeMatch = rest.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):/);
  if (schemeMatch) {
    scheme = schemeMatch[1].toLowerCase();
    rest = rest.slice(schemeMatch[0].length);
  }
  if (rest.startsWith("//")) {
    rest = rest.slice(2);
    let end = rest.length;
    for (const ch of ["/", "?", "#"]) {
      const idx = rest.indexOf(ch);
      if (idx >= 0 && idx < end) end = idx;
    }
    netloc = rest.slice(0, end);
    rest = rest.slice(end);
  }
  const qIdx = rest.indexOf("?");
  if (qIdx >= 0) {
    query = rest.slice(qIdx + 1);
    rest = rest.slice(0, qIdx);
  }
  return { scheme, netloc, path: rest, query, fragment };
}

function canonicalNormalize(url) {
  const parts = urlsplit(url);
  let path = parts.path.replace(/\/+$/, "") || "/";
  return `${parts.scheme.toLowerCase()}://${parts.netloc.toLowerCase()}${path}${parts.query ? "?" + parts.query : ""}`;
}

function audit_canonical(pageUrl, canonicalUrl) {
  if (!canonicalUrl) {
    return {
      ok: false,
      findings: [finding("SEO-CANONICAL-001", "medium", "Canonical URL is missing",
        "No canonical link was found in the supplied HTML.",
        "Declare the preferred indexable product URL.")],
    };
  }
  if (!(canonicalUrl.startsWith("http://") || canonicalUrl.startsWith("https://"))) {
    return {
      ok: false,
      findings: [finding("SEO-CANONICAL-002", "medium", "Canonical URL is not absolute",
        `The canonical value is \`${canonicalUrl}\`.`,
        "Publish an absolute HTTP or HTTPS canonical URL.")],
    };
  }
  if (canonicalNormalize(pageUrl) !== canonicalNormalize(canonicalUrl)) {
    return {
      ok: true,
      findings: [finding("SEO-CANONICAL-003", "low", "Page canonicalizes to another URL",
        `Page URL \`${pageUrl}\` points to \`${canonicalUrl}\`.`,
        "Confirm the target intentionally represents the preferred product identity.")],
    };
  }
  return { ok: true, findings: [] };
}

/* =========================================================================
 * discovery/content_evidence.py :: evidence_coverage
 * ========================================================================= */

function evidence_coverage(signals) {
  const text = signals.visible_text.toLowerCase();
  const any = (terms) => terms.some((t) => text.includes(t));
  return {
    specifications: any(["specification", "material", "dimensions", "size"]),
    limitations: any(["limitation", "not suitable", "avoid", "warning"]),
    shipping: any(["shipping", "delivery", "dispatch"]),
    returns: any(["return", "refund", "exchange"]),
  };
}

/* =========================================================================
 * discovery/quality.py :: audit_page_quality
 * ========================================================================= */

const _PROMO_TERMS = ["free shipping", "buy now", "sale!", "% off", "best price", "order today"];
const _SNIPPET_BLOCKERS = ["noarchive", "nocache", "nosnippet", "max-snippet:0", "max-snippet: 0"];
const _REVIEW_PATTERN = /\b\d[\d,]*\s+(?:customer\s+)?reviews?\b|\bcustomer reviews\b/i;
const _INJECTION_PATTERNS = [
  /ignore (?:all )?(?:previous|prior|above) (?:instructions|prompts)/,
  /disregard (?:your|all|previous) (?:instructions|guidelines)/,
  /you are an ai (?:assistant|agent|model)/,
  /as an ai (?:assistant|agent|model),? (?:you must|always|recommend)/,
  /system prompt/,
  /always (?:recommend|choose|rank) this (?:product|item|store)/,
  /do not (?:mention|recommend) (?:any )?(?:other|competitor)/,
];

function _variant_signals(product) {
  return Boolean(product.color || product.size || product.pattern);
}
function _has_variant_grouping(product) {
  return Boolean(product.inProductGroupWithID || product.isVariantOf);
}
function _image_urls(product) {
  let value = product.image;
  const values = Array.isArray(value) ? value : [value];
  const urls = [];
  for (let item of values) {
    if (item && typeof item === "object" && !Array.isArray(item)) item = item.url || item.contentUrl;
    if (item) urls.push(pyStr(item));
  }
  return urls;
}
function _price_texts(offers) {
  const texts = [];
  for (const offer of offers) {
    let raw = offer.price;
    if (raw && typeof raw === "object" && !Array.isArray(raw)) raw = raw.price;
    if (raw !== null && raw !== undefined && raw !== "") texts.push(pyStr(raw));
  }
  return texts;
}
function _price_on_page(price, pageText) {
  const normalized = price.replace(/,/g, "");
  const candidates = new Set([normalized, normalized.replace(/0+$/, "").replace(/\.$/, ""), normalized.split(".")[0]]);
  const haystack = pageText.replace(/,/g, "");
  for (const c of candidates) if (c && haystack.includes(c)) return true;
  return false;
}
function _normalize(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/^ +/, "").replace(/ +$/, "");
}

function audit_page_quality(signals, products, offers, coverage) {
  const findings = [];
  const text = signals.visible_text;
  const lowered = text.toLowerCase();

  // GEO-PRODUCT-003
  const page_haystack = _normalize(`${signals.title} ${text}`);
  for (const product of products) {
    const name = product.name;
    if (typeof name !== "string" || name.trim().length < 3) continue;
    if (!page_haystack.includes(_normalize(name))) {
      findings.push(finding("GEO-PRODUCT-003", "high", "Product name in markup does not match the visible page",
        `JSON-LD names the product “${name.trim()}”, which does not appear in the page title or text.`,
        "Use the real, shopper-facing product name in structured data; agents read the markup name, not the page."));
      break;
    }
  }

  // GEO-OFFER-003
  const prices = _price_texts(offers);
  if (prices.length && signals.visible_words >= 30 && !prices.some((p) => _price_on_page(p, text))) {
    findings.push(finding("GEO-OFFER-003", "low", "Machine-readable price is not visible in the page text",
      `No offer price (${prices.slice(0, 3).join(", ")}) appears in the supplied HTML text.`,
      "Confirm the visible price matches the markup; mismatches are a documented disapproval cause."));
  }

  // GEO-RETURNS-001
  const has_return_markup = offers.some((o) => o.hasMerchantReturnPolicy) || products.some((p) => p.hasMerchantReturnPolicy);
  if (products.length && !has_return_markup && !coverage.returns) {
    findings.push(finding("GEO-RETURNS-001", "medium", "Return policy is missing",
      "No hasMerchantReturnPolicy markup and no visible returns information were found.",
      "State the return policy on the page; AI shopping feeds require a return policy."));
  }

  // GEO-SHIPPING-001
  const has_shipping_markup = offers.some((o) => o.shippingDetails);
  if (products.length && !has_shipping_markup && !coverage.shipping) {
    findings.push(finding("GEO-SHIPPING-001", "low", "Shipping information is missing",
      "No shippingDetails markup and no visible shipping information were found.",
      "State shipping cost and time on the page or add machine-readable shippingDetails."));
  }

  // GEO-IMAGE-001
  const bad_images = [];
  for (const product of products) for (const url of _image_urls(product)) {
    if (!(url.startsWith("http://") || url.startsWith("https://"))) bad_images.push(url);
  }
  if (bad_images.length) {
    findings.push(finding("GEO-IMAGE-001", "low", "Product image URLs are not crawlable absolute URLs",
      `Non-absolute image references: ${bad_images.slice(0, 3).join(", ")}.`,
      "Publish absolute http(s) image URLs that crawlers can fetch and index."));
  }

  // GEO-VARIANT-001
  for (const product of products) {
    if (_variant_signals(product) && !_has_variant_grouping(product)) {
      findings.push(finding("GEO-VARIANT-001", "low", "Variant attributes lack variant-group markup",
        "The Product declares color/size/pattern but no inProductGroupWithID or isVariantOf.",
        "Link variants with inProductGroupWithID or isVariantOf so agents group them correctly."));
      break;
    }
  }

  // GEO-RATING-001
  const has_rating_markup = products.some((p) => p.aggregateRating);
  if (products.length && !has_rating_markup && _REVIEW_PATTERN.test(text)) {
    findings.push(finding("GEO-RATING-001", "low", "Visible reviews lack AggregateRating markup",
      "The page text mentions reviews but no aggregateRating is machine-readable.",
      "Publish AggregateRating with ratingValue and reviewCount matching the visible reviews."));
  }

  // SEO-TITLE-002
  const title = signals.title;
  if (title) {
    const problems = [];
    if (title.length > 150) problems.push(`${title.length} characters (limit 150)`);
    const promo = _PROMO_TERMS.filter((term) => title.toLowerCase().includes(term));
    if (promo.length) problems.push(`promotional text (${promo.join(", ")})`);
    const letters = [...title].filter((ch) => isAlpha(ch));
    if (letters.length >= 12 && letters.filter((ch) => isUpper(ch)).length / letters.length > 0.8) {
      problems.push("mostly capital letters");
    }
    if (problems.length) {
      findings.push(finding("SEO-TITLE-002", "medium", "Title violates product-title conventions",
        `The title has ${problems.join("; ")}.`,
        "Use a plain, accurate product title: no promotions, no all-caps, at most 150 characters."));
    }
  }

  // SEO-SNIPPET-001
  const robots = signals.robots.replace(/ /g, "");
  const blockers = _SNIPPET_BLOCKERS.filter((token) => robots.includes(token.replace(/ /g, "")));
  if (blockers.length) {
    findings.push(finding("SEO-SNIPPET-001", "medium", "Snippet or caching restrictions limit AI answers",
      `robots meta contains: ${[...new Set(blockers)].sort().join(", ")}.`,
      "Remove noarchive/nocache/nosnippet unless intentional; they reduce or block Copilot citations."));
  }

  // GEO-CONDITION-001
  const condition_terms = [...lowered.matchAll(/\b(refurbished|pre-owned|preowned|open box|open-box|second-hand|secondhand)\b/g)].map((m) => m[1]);
  if (products.length && condition_terms.length) {
    const has_condition = offers.some((o) => o.itemCondition) || products.some((p) => p.itemCondition);
    if (!has_condition) {
      findings.push(finding("GEO-CONDITION-001", "medium", "Non-new product lacks itemCondition markup",
        `The page mentions “${condition_terms[0]}” but no offer declares itemCondition.`,
        "Declare itemCondition (RefurbishedCondition/UsedCondition); feeds require condition for non-new products."));
    }
  }

  // SEO-DESC-001
  if (products.length && !signals.description) {
    findings.push(finding("SEO-DESC-001", "low", "Meta description is missing",
      "No meta description was found in the supplied HTML.",
      "Add an accurate meta description; missing descriptions reduce snippet and grounding reliability."));
  }

  // SEO-LANG-001
  if (products.length && !signals.lang) {
    findings.push(finding("SEO-LANG-001", "low", "The html element declares no lang attribute",
      "No lang attribute was found on the html element.",
      'Declare the page language (e.g. <html lang="en">) so agents parse and localize correctly.'));
  }

  // GEO-POLICY-001
  if (products.length) {
    const link_blobs = signals.links.map(([href, t]) => `${href.toLowerCase()} ${t}`);
    const has_privacy = link_blobs.some((blob) => blob.includes("privacy"));
    const has_terms = link_blobs.some((blob) => blob.includes("terms") || blob.includes("conditions") || /\btos\b/.test(blob));
    const missing = [];
    if (!has_privacy) missing.push("privacy policy");
    if (!has_terms) missing.push("terms of service");
    if (missing.length) {
      findings.push(finding("GEO-POLICY-001", "medium", "Checkout trust links are missing",
        `No link to a ${missing.join(" or ")} was found on the page.`,
        "Link the privacy policy and terms of service; agentic checkout requires both as functional URLs."));
    }
  }

  // SEO-HTTPS-001
  const insecure = [];
  if ((signals.canonical || "").startsWith("http://")) insecure.push(`canonical: ${signals.canonical}`);
  for (const product of products) for (const url of _image_urls(product)) {
    if (url.startsWith("http://")) insecure.push(`image: ${url}`);
  }
  if (insecure.length) {
    findings.push(finding("SEO-HTTPS-001", "medium", "Product URLs are not HTTPS",
      `Insecure URL(s): ${insecure.slice(0, 3).join("; ")}.`,
      "Serve canonical and image URLs over HTTPS; agents and checkout flows treat http:// as untrusted."));
  }

  // CLAIM-INJECTION-001
  const injected = _INJECTION_PATTERNS.filter((pattern) => pattern.test(lowered));
  if (injected.length) {
    const match = lowered.match(injected[0]);
    findings.push(finding("CLAIM-INJECTION-001", "high", "Page text attempts to manipulate AI agents",
      `Prompt-injection-style text found: “${match ? match[0] : injected[0]}”.`,
      "Remove instructions aimed at AI systems; platforms treat this as abuse and may delist the page."));
  }

  return findings;
}

function isAlpha(ch) {
  // Python str.isalpha for a single char (Unicode letter). Approximate with Unicode property.
  return /\p{L}/u.test(ch);
}
function isUpper(ch) {
  return /\p{Lu}/u.test(ch) || (/\p{Lt}/u.test(ch));
}

/* =========================================================================
 * discovery/scoring.py :: audit_page_html
 * ========================================================================= */

function audit_page_html(url, html) {
  const parts = urlsplit(url);
  if (!(parts.scheme === "http" || parts.scheme === "https") || !parts.netloc) {
    throw new Error("url must be an absolute HTTP or HTTPS URL");
  }
  const signals = new PageSignals();
  signals.feed(html);
  const findings = [];

  const title_ok = Boolean(signals.title);
  if (!title_ok) {
    findings.push(finding("SEO-TITLE-001", "high", "Page title is missing",
      "No non-empty title element was found.",
      "Add a concise title that accurately identifies the product."));
  }

  const canon = audit_canonical(url, signals.canonical);
  const canonical_ok = canon.ok;
  findings.push(...canon.findings);

  const indexable = !signals.robots.includes("noindex");
  if (!indexable) {
    findings.push(finding("SEO-ROBOTS-001", "high", "Page requests noindex",
      `robots content is \`${signals.robots}\`.`,
      "Remove noindex only if public discovery is intended."));
  }

  const sd = audit_product_structured_data(signals.json_ld_blocks);
  findings.push(...sd.findings);

  const evidence = evidence_coverage(signals);
  const substantive = signals.visible_words >= 120;
  if (!substantive) {
    findings.push(finding("GEO-EVIDENCE-001", "medium", "Product evidence is thin",
      `Only ${signals.visible_words} visible words were detected.`,
      "Add verified specifications, use cases, limitations, shipping, and return information."));
  }
  const missing_evidence = Object.keys(evidence).filter((name) => !evidence[name]);
  if (missing_evidence.length) {
    findings.push(finding("GEO-EVIDENCE-002", "low", "Product evidence coverage is incomplete",
      `Missing evidence areas: ${missing_evidence.join(", ")}.`,
      "Add concise shopper-facing facts only where the merchant can support them."));
  }

  findings.push(...audit_page_quality(signals, sd.products, sd.offers, evidence));

  const summary = {
    title: signals.title || null,
    description: signals.description || null,
    canonical: signals.canonical,
    visible_words: signals.visible_words,
    evidence_coverage: evidence,
    ...sd.summary,
    findings: findings.length,
  };
  return { operation: "audit_page_html", summary, findings, checks: sd.checks };
}

/* =========================================================================
 * optimization/claims.py :: audit_listing_claims
 * ========================================================================= */

const _SUPERLATIVE_PATTERNS = [
  /#\s?1\b/gi, /\bworld'?s (?:best|leading|first)\b/gi, /\bbest[- ]selling\b/gi,
  /\bthe best\b/gi, /\bnumber one\b/gi, /\bmarket[- ]leading\b/gi,
];
const _RATED_PATTERNS = [/\btop[- ]rated\b/gi, /\bhighest[- ]rated\b/gi, /\bfive[- ]star\b/gi, /\b5[- ]star\b/gi];
const _PROOF_PATTERNS = [
  /\bclinically (?:proven|tested)\b/gi, /\bscientifically proven\b/gi, /\bdoctor (?:recommended|approved)\b/gi,
  /\bdermatologist (?:recommended|tested)\b/gi, /\bmedical[- ]grade\b/gi, /\bfda[- ](?:approved|cleared)\b/gi,
  /\blab[- ](?:tested|certified)\b/gi,
];
const _WARRANTY_PATTERNS = [
  /\blifetime (?:warranty|guarantee)\b/gi, /\b\d+[- ](?:year|month)s?[- ](?:warranty|guarantee)\b/gi,
  /\bmoney[- ]back guarantee\b/gi,
];
const _PERFORMANCE_PATTERNS = [
  /\bwaterproof\b/gi, /\bwater[- ]resistant\b/gi, /\bunbreakable\b/gi, /\bindestructible\b/gi,
  /\bscratch[- ]proof\b/gi, /\bstain[- ]proof\b/gi, /\bfire[- ](?:proof|resistant)\b/gi,
  /\bhypoallergenic\b/gi, /\bantibacterial\b/gi, /\bnon[- ]toxic\b/gi, /\b100%\s+\w+/gi,
];

function _claim_matches(patterns, text) {
  const found = [];
  const lowerSet = new Set();
  for (const pattern of patterns) {
    pattern.lastIndex = 0;
    let m;
    while ((m = pattern.exec(text)) !== null) {
      const phrase = m[0].replace(/\s+/g, " ").trim();
      if (!lowerSet.has(phrase.toLowerCase())) {
        found.push(phrase);
        lowerSet.add(phrase.toLowerCase());
      }
      if (m[0].length === 0) pattern.lastIndex++;
    }
  }
  return found;
}

function _grounded(phrases, evidenceText) {
  const grounded = [];
  const ungrounded = [];
  for (const phrase of phrases) {
    const key = phrase.toLowerCase().replace(/[^a-z0-9 ]/g, "").replace(/^ +/, "").replace(/ +$/, "");
    const tokens = key.split(/\s+/).filter((t) => t.length > 3);
    if (tokens.length && tokens.every((t) => evidenceText.includes(t))) grounded.push(phrase);
    else ungrounded.push(phrase);
  }
  return { grounded, ungrounded };
}

function _quote(phrases) {
  return phrases.slice(0, 5).map((p) => `“${p}”`).join(", ");
}

function audit_listing_claims(evidenceRecord) {
  const product = evidenceRecord.product || {};
  const listing_text = ["title", "description"].map((f) => pyStr(product[f] || "")).join(" ");
  const review = product.review_summary || {};
  const has_review_evidence = Boolean(review.rating && review.count);

  const evidence_parts = [];
  for (const item of evidenceRecord.evidence || []) {
    const identifier = pyStr(item.id || "");
    if (identifier.startsWith("spec.") || identifier.startsWith("page.") || identifier.startsWith("review.")) {
      evidence_parts.push(pyStr(item.value || ""));
    }
  }
  const evidence_text = evidence_parts.join(" ").toLowerCase().replace(/[^a-z0-9 ]/g, " ");

  const findings = [];

  const superlatives = _claim_matches(_SUPERLATIVE_PATTERNS, listing_text);
  if (superlatives.length) {
    findings.push(finding("CLAIM-SUPERLATIVE-001", "medium", "Unverifiable superlative claims in listing copy",
      `The title or description states ${_quote(superlatives)} without citable support.`,
      "Remove rank claims or replace them with specific, verifiable product facts."));
  }

  const rated = _claim_matches(_RATED_PATTERNS, listing_text);
  if (rated.length && !has_review_evidence) {
    findings.push(finding("CLAIM-RATING-001", "medium", "Rating claims lack review evidence",
      `The listing states ${_quote(rated)} but no aggregate rating and review count were found.`,
      "Publish machine-readable AggregateRating data or remove the rating claim."));
  }

  const proof = _claim_matches(_PROOF_PATTERNS, listing_text);
  if (proof.length) {
    const { ungrounded } = _grounded(proof, evidence_text);
    if (ungrounded.length) {
      findings.push(finding("CLAIM-PROOF-001", "high", "Scientific or medical claims lack evidence",
        `The listing states ${_quote(ungrounded)} with no supporting evidence on the page.`,
        "Cite the specific test, certification, or approval on the page, or remove the claim."));
    }
  }

  const warranty = _claim_matches(_WARRANTY_PATTERNS, listing_text);
  if (warranty.length) {
    const has_warranty_evidence = (evidenceRecord.evidence || []).some((item) => pyStr(item.id) === "page.warranty");
    if (!has_warranty_evidence) {
      findings.push(finding("CLAIM-WARRANTY-001", "high", "Warranty or guarantee claims lack page evidence",
        `The listing states ${_quote(warranty)} but no warranty terms appear on the page.`,
        "State the warranty terms on the page or remove the guarantee claim."));
    }
  }

  const performance = _claim_matches(_PERFORMANCE_PATTERNS, listing_text);
  if (performance.length) {
    const { ungrounded } = _grounded(performance, evidence_text);
    if (ungrounded.length) {
      findings.push(finding("CLAIM-PERFORMANCE-001", "medium", "Performance claims lack supporting evidence",
        `The listing states ${_quote(ungrounded)} without matching specification or page evidence.`,
        "Back each performance claim with a specification, standard, or visible product fact."));
    }
  }

  return findings;
}

/* =========================================================================
 * optimization/readiness.py :: score_page_readiness
 * ========================================================================= */

const _CLAIM_DEDUCTIONS = { high: 5, medium: 3, low: 1 };
const _FINDING_DEDUCTIONS = { high: 6, medium: 3, low: 1 };
const _GEO_DEDUCTIONS = { high: 9, medium: 5, low: 2 };

function _deduction(item) {
  const table = String(item.rule_id || "").startsWith("GEO-") ? _GEO_DEDUCTIONS : _FINDING_DEDUCTIONS;
  const sev = String(item.severity);
  return Object.prototype.hasOwnProperty.call(table, sev) ? table[sev] : 1;
}

function _metric_breakdown(findings) {
  const breakdown = {};
  for (const metric of METRICS) {
    const matching = findings.filter((item) => (item.metric || metric_for(item.rule_id || "")) === metric);
    const deductions = matching.reduce((s, item) => s + _deduction(item), 0);
    breakdown[metric] = { status: matching.length ? "needs_work" : "clear", findings: matching.length, deductions };
  }
  return breakdown;
}

function _platform_scores(raw_score, findings, cap_events) {
  const views = ["comprehensive", ...PLATFORMS];
  const output = {};
  for (const platform of views) {
    let relevant_findings, relevant_caps, label, surfaces;
    if (platform === "comprehensive") {
      relevant_findings = findings;
      relevant_caps = cap_events;
      label = "Comprehensive";
      surfaces = [];
      for (const name of PLATFORMS) for (const surface of PLATFORM_SURFACES[name]) surfaces.push(surface);
    } else {
      relevant_findings = findings.filter((item) => (item.platforms || platforms_for(item.rule_id || "")).includes(platform));
      relevant_caps = cap_events.filter((event) => event.platforms.includes(platform));
      label = PLATFORM_LABELS[platform];
      surfaces = PLATFORM_SURFACES[platform];
    }
    const deductions = relevant_findings.reduce((s, item) => s + _deduction(item), 0);
    const cap = relevant_caps.length ? Math.min(...relevant_caps.map((e) => parseInt(e.cap, 10))) : 100;
    const score = Math.max(1, Math.min(raw_score - deductions, cap));
    output[platform] = {
      label,
      surfaces: [...surfaces],
      score,
      status: score >= 80 && cap === 100 ? "ready" : "needs_work",
      raw_score,
      deductions,
      deduction_items: relevant_findings.map((item) => ({
        rule_id: String(item.rule_id || ""),
        title: String(item.title || "Finding"),
        metric: String(item.metric || metric_for(item.rule_id || "")),
        severity: String(item.severity || "low"),
        points: _deduction(item),
      })),
      safety_cap: cap,
      cap_reasons: relevant_caps.map((e) => String(e.reason)),
      findings: relevant_findings.length,
      metrics: _metric_breakdown(relevant_findings),
    };
  }
  return output;
}

const PILLARS = [
  "product_identity", "offer_completeness", "structured_data", "decision_evidence",
  "media_variants", "claim_grounding",
];

function score_page_readiness(evidenceRecord, pageAudit, claimFindings) {
  const product = evidenceRecord.product || {};
  const price = product.price || {};
  const summary = pageAudit.summary || {};
  const page_findings = pageAudit.findings || [];
  claimFindings = claimFindings || [];

  const clean_of = (ruleId) => !page_findings.some((item) => item.rule_id === ruleId);

  const stable_id = Boolean(product.id || product.sku || product.gtin || product.mpn);
  const identity_checks = {
    title: [Boolean(product.title), 5],
    brand: [Boolean(product.brand), 5],
    category: [Boolean(product.category), 4],
    stable_identifier: [stable_id, 4],
    canonical_url: [Boolean(product.url), 2],
  };
  const offer_complete_markup = Boolean(summary.offers) && clean_of("GEO-OFFER-001") && clean_of("GEO-OFFER-002");
  const offer_checks = {
    price: [Boolean(price.amount), 6],
    currency: [Boolean(price.currency), 4],
    availability: [Boolean(product.availability), 6],
    complete_offer_markup: [offer_complete_markup, 4],
  };
  const structured_checks = {
    product_node: [Boolean(summary.products), 6],
    product_identity: [Boolean(summary.products) && clean_of("GEO-PRODUCT-002") && clean_of("GEO-PRODUCT-003"), 4],
    offer: [offer_complete_markup, 5],
    canonical: [Boolean(summary.canonical), 3],
    valid_json_ld: [(summary.invalid_json_ld || 0) === 0, 2],
  };
  const coverage = summary.evidence_coverage || {};
  const review = product.review_summary || {};
  const decision_checks = {
    description: [Boolean(product.description), 4],
    specifications: [Boolean(product.specifications && product.specifications.length), 4],
    substantive_page: [parseInt(summary.visible_words || 0, 10) >= 120, 3],
    evidence_topics: [Object.values(coverage).filter((v) => Boolean(v)).length >= 3, 3],
    review_evidence: [Boolean(review.rating && review.count), 1],
  };
  const specifications = product.specifications || [];
  const variant_evidence = specifications.some(
    (item) => item && typeof item === "object" && ["color", "size", "pattern"].includes(String(item.name || "").toLowerCase())
  );
  const images = product.images || [];
  const media_checks = {
    primary_image: [Boolean(images.length), 8],
    multiple_images: [images.length >= 2, 3],
    variant_attribute: [variant_evidence, 2],
    variant_identity: [Boolean(product.sku || product.id), 2],
  };

  const groups = {
    product_identity: identity_checks,
    offer_completeness: offer_checks,
    structured_data: structured_checks,
    decision_evidence: decision_checks,
    media_variants: media_checks,
  };
  const components = {};
  let raw_score = 0;
  for (const [name, checks] of Object.entries(groups)) {
    let score = 0;
    let maximum = 0;
    const checkStates = {};
    for (const [key, [passed, weight]] of Object.entries(checks)) {
      if (passed) score += weight;
      maximum += weight;
      checkStates[key] = passed;
    }
    raw_score += score;
    components[name] = { score, max_score: maximum, checks: checkStates };
  }

  const claim_deduction = claimFindings.reduce(
    (s, item) => s + (Object.prototype.hasOwnProperty.call(_CLAIM_DEDUCTIONS, String(item.severity)) ? _CLAIM_DEDUCTIONS[String(item.severity)] : 1),
    0
  );
  const claim_score = Math.max(0, 10 - claim_deduction);
  raw_score += claim_score;
  components.claim_grounding = {
    score: claim_score,
    max_score: 10,
    checks: {
      no_high_risk_claims: !claimFindings.some((item) => item.severity === "high"),
      no_unsupported_claims: claimFindings.length === 0,
    },
  };

  const cap_events = [];
  if (claimFindings.some((item) => item.severity === "high")) {
    cap_events.push({ cap: 49, reason: "An unsupported high-risk claim was found in the listing copy.", platforms: PLATFORMS });
  }
  if (!clean_of("CLAIM-INJECTION-001")) {
    cap_events.push({ cap: 49, reason: "The page contains text aimed at manipulating AI agents.", platforms: PLATFORMS });
  }
  if (!stable_id) {
    cap_events.push({ cap: 59, reason: "A stable product identifier is missing.", platforms: PLATFORMS });
  }
  if (!(price.amount && price.currency && product.availability)) {
    cap_events.push({ cap: 69, reason: "Price, currency, or availability evidence is incomplete.", platforms: PLATFORMS });
  }
  if (!summary.products) {
    cap_events.push({ cap: 74, reason: "No Product structured data was found on the page.", platforms: ["google", "microsoft"] });
  }

  const scored_findings = [...page_findings, ...claimFindings];
  const platform_scores = _platform_scores(raw_score, scored_findings, cap_events);
  const comprehensive = platform_scores.comprehensive;
  return {
    score: comprehensive.score,
    raw_score,
    deductions: comprehensive.deductions,
    status: comprehensive.status,
    components,
    safety_cap: comprehensive.safety_cap,
    cap_reasons: comprehensive.cap_reasons,
    platform_scores,
    observed_ai_visibility: { status: "not_measured", score: null },
  };
}

/* =========================================================================
 * agent/tools.py :: build_agent_findings (top-level display findings + dedup)
 * ========================================================================= */

function _missing_finding(ruleId, severity, title, fieldName, recommendation) {
  return finding(ruleId, severity, title,
    `No verified \`${fieldName}\` value is present in the supplied evidence.`,
    recommendation, "agent_deterministic_rule");
}

function build_agent_findings(evidenceRecord, pageAudit, claimFindings) {
  const product = evidenceRecord.product || {};
  const price = product.price || {};
  const findings = (pageAudit.findings || []).map((item) => structuredClone(item));
  for (const item of claimFindings || []) findings.push(structuredClone(item));
  const additions = [];
  if (!(product.id || product.sku || product.gtin || product.mpn)) {
    additions.push(_missing_finding("AGENT-IDENTITY-001", "high", "Stable product identity is missing", "id/sku/gtin/mpn", "Supply a verified stable product or variant identifier."));
  }
  if (!product.brand) additions.push(_missing_finding("AGENT-BRAND-001", "medium", "Brand evidence is missing", "brand", "Confirm the merchant or manufacturer brand."));
  if (!product.category) additions.push(_missing_finding("AGENT-CATEGORY-001", "medium", "Product category is missing", "category", "Supply a verified merchant category or taxonomy path."));
  if (!price.amount) additions.push(_missing_finding("AGENT-OFFER-PRICE", "high", "Price evidence is missing", "price", "Supply the current verified price."));
  if (!price.currency) additions.push(_missing_finding("AGENT-OFFER-CURRENCY", "high", "Currency evidence is missing", "currency", "Supply the ISO 4217 price currency."));
  if (!product.availability) additions.push(_missing_finding("AGENT-OFFER-AVAILABILITY", "high", "Availability evidence is missing", "availability", "Supply the current verified availability state."));
  if (!(product.images && product.images.length)) additions.push(_missing_finding("AGENT-IMAGE-001", "medium", "Primary product image is missing", "image", "Supply the canonical product image URL."));
  if (!product.description) additions.push(_missing_finding("AGENT-DESCRIPTION-001", "medium", "Product description evidence is missing", "description", "Supply a factual merchant-approved description."));

  const seen = new Set(findings.map((item) => String(item.rule_id)));
  for (const item of additions) if (!seen.has(item.rule_id)) findings.push(item);
  return findings;
}

/* =========================================================================
 * Public API — mirrors CLI result["readiness"]["before"] + top-level findings
 * ========================================================================= */

export function auditProductPage(html, url) {
  const evidence_record = evidence_from_html(url, html);
  const claim_findings = audit_listing_claims(evidence_record);
  const page_audit = audit_page_html(url, html);
  const before = score_page_readiness(evidence_record, page_audit, claim_findings);
  const findings = build_agent_findings(evidence_record, page_audit, claim_findings);
  return { ...before, findings };
}

export {
  evidence_from_html, audit_page_html, audit_listing_claims, score_page_readiness,
  build_agent_findings, is_valid_gtin, unescape, ProductHTMLParser, PageSignals,
};
