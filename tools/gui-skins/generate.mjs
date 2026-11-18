#!/usr/bin/env node
// Generates the GUI skin background textures, overlay glyphs and the gui_skins bitmap font
// from tools/gui-skins/skins.json (source of truth). Built-ins only. Deterministic/idempotent.
// Usage: node tools/gui-skins/generate.mjs
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { CONTROLS, CHAPTER_ART, artOf } from './icons.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '..', '..');
const spec = JSON.parse(fs.readFileSync(path.join(here, 'skins.json'), 'utf8'));
const texDir = path.join(root, spec.texture_dir);
const fontFile = path.join(root, 'assets/sovereignmc/font/gui_skins.json');

// ---------- minimal PNG encoder ----------
const CRC_T = new Uint32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
function crc32(buf) { let c = 0xFFFFFFFF; for (const b of buf) c = CRC_T[(c ^ b) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
function chunk(type, data) {
  const out = Buffer.alloc(12 + data.length);
  out.writeUInt32BE(data.length, 0); out.write(type, 4, 'ascii'); data.copy(out, 8);
  out.writeUInt32BE(crc32(out.subarray(4, 8 + data.length)), 8 + data.length);
  return out;
}
function encodePng(w, h, rgba) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6;
  const raw = Buffer.alloc((w * 4 + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w * 4 + 1)] = 0; Buffer.from(rgba.buffer, rgba.byteOffset + y * w * 4, w * 4).copy(raw, y * (w * 4 + 1) + 1); }
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', ihdr), chunk('IDAT', zlib.deflateSync(raw, { level: 9 })), chunk('IEND', Buffer.alloc(0))]);
}

function decodePng(buf) {
  if (!buf.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) throw new Error('not a PNG');
  let pos = 8, w = 0, h = 0; const idat = [];
  while (pos < buf.length) {
    const len = buf.readUInt32BE(pos), type = buf.toString('ascii', pos + 4, pos + 8), data = buf.subarray(pos + 8, pos + 8 + len);
    if (type === 'IHDR') { w = data.readUInt32BE(0); h = data.readUInt32BE(4); if (data[8] !== 8 || data[9] !== 6 || data[12] !== 0) throw new Error('only 8-bit RGBA non-interlaced PNG supported'); }
    else if (type === 'IDAT') idat.push(data);
    pos += 12 + len;
  }
  const raw = zlib.inflateSync(Buffer.concat(idat)), stride = w * 4, out = Buffer.alloc(stride * h);
  for (let y = 0; y < h; y++) {
    const ft = raw[y * (stride + 1)], line = raw.subarray(y * (stride + 1) + 1, (y + 1) * (stride + 1));
    for (let i = 0; i < stride; i++) {
      const a = i >= 4 ? out[y * stride + i - 4] : 0, b = y ? out[(y - 1) * stride + i] : 0, c = i >= 4 && y ? out[(y - 1) * stride + i - 4] : 0;
      let pr;
      if (ft === 0) pr = 0; else if (ft === 1) pr = a; else if (ft === 2) pr = b; else if (ft === 3) pr = (a + b) >> 1;
      else if (ft === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); pr = pa <= pb && pa <= pc ? a : pb <= pc ? b : c; }
      else throw new Error('bad PNG filter ' + ft);
      out[y * stride + i] = (line[i] + pr) & 255;
    }
  }
  return { w, h, data: out };
}

// ---------- tiny software canvas ----------
function rgb(h) { h = h.replace('#', ''); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
class Canvas {
  constructor(w, h) { this.w = w; this.h = h; this.data = new Uint8ClampedArray(w * h * 4); this.fillStyle = '#000000'; }
  fillRect(x, y, w, h) {
    const [r, g, b] = rgb(this.fillStyle);
    for (let j = Math.max(0, y); j < Math.min(this.h, y + h); j++) for (let i = Math.max(0, x); i < Math.min(this.w, x + w); i++) {
      const k = (j * this.w + i) * 4; this.data[k] = r; this.data[k + 1] = g; this.data[k + 2] = b; this.data[k + 3] = 255;
    }
  }
  clearRect(x, y, w, h) {
    for (let j = Math.max(0, y); j < Math.min(this.h, y + h); j++) for (let i = Math.max(0, x); i < Math.min(this.w, x + w); i++) {
      const k = (j * this.w + i) * 4; this.data[k] = this.data[k + 1] = this.data[k + 2] = this.data[k + 3] = 0;
    }
  }
  png() { return encodePng(this.w, this.h, this.data); }
}

function drawGrid(ctx, g, x, y) { for (let r = 0; r < 16; r++) for (let c = 0; c < 16; c++) if (g[r][c]) { ctx.fillStyle = g[r][c]; ctx.fillRect(x + c, y + r, 1, 1); } }

// ---------- palettes ----------
const ACC = { extraction: '#d99a2b', processing: '#d0693a', power: '#33b6cf', military: '#8f9d3c', crafting: '#b9874b', arcane: '#9b5bd6', admin: '#d4b048', guide: '#a0442c' };
const SKINS = {
  steel: { base: '#b4b8bd', hi: '#eceef0', lo: '#676c73', rim: '#141619', ink: '#3a3f46', bay: '#2a2e34', bayHi: '#474d55', bayLo: '#111316', sock: '#3a3f47', sockHi: '#5d646e', sockLo: '#15171b', dim: '#30343a', lcd: '#0c1712', lcdOn: '#55e394', lcdOff: '#173022', plate: '#c8cbcf', plateHi: '#f2f3f5', plateLo: '#7d838b', bayInk: '#8e98a5', hatch: '#3c4249', title: '#3b3f45' },
  guide: { base: '#e2d2a6', hi: '#f6ecce', lo: '#a3884f', rim: '#2a170a', ink: '#5b3b1d', bay: '#cdb683', bayHi: '#e6d6aa', bayLo: '#977c49', sock: '#bba26c', sockHi: '#ddc995', sockLo: '#7f6537', dim: '#c6af7c', lcd: '#3a2918', lcdOn: '#f2c463', lcdOff: '#58402a', plate: '#d6c28d', plateHi: '#f1e5bf', plateLo: '#9b814d', bayInk: '#6f5228', hatch: '#b59c66', title: '#4a2f14', leather: '#6b3a20', leatherHi: '#8a5230', leatherLo: '#3f1f0f' },
};
SKINS.admin = Object.assign({}, SKINS.steel, { base: '#b3b8c2', bay: '#232a3a', bayHi: '#3b4560', bayLo: '#0e121b', sock: '#323b52', sockHi: '#56617f', sockLo: '#121725', dim: '#2a3245', bayInk: '#8f9bb8', hatch: '#344058', plate: '#c6cbd5' });
const RIM = { c: '#33b6cf', f: '#e08a2e', k: '#8a5a2b' };
const PIN = ["..rrr...", ".rrwrr..", ".rrrrr..", "..rrr...", "...d....", "...d....", "...d....", "........"];
const PIN_PAL = { r: '#c0392b', w: '#f4f4f4', d: '#4a4a4a' };

// ---------- 3x5 pixel font ----------
const F = { A: "010101111101101", B: "110101110101110", C: "011100100100011", D: "110101101101110", E: "111100110100111", F: "111100110100100", G: "011100101101011", H: "101101111101101", I: "111010010010111", J: "001001001101010", K: "101101110101101", L: "100100100100111", M: "101111111101101", N: "110101101101101", O: "010101101101010", P: "110101110100100", Q: "010101101110011", R: "110101110101101", S: "011100010001110", T: "111010010010010", U: "101101101101111", V: "101101101101010", W: "101101111111101", X: "101101010101101", Y: "101101010010010", Z: "111001010100111", "0": "111101101101111", "1": "010110010010111", "2": "110001010100111", "3": "110001010001110", "4": "101101111001001", "5": "111100110001110", "6": "011100110101010", "7": "111001010010010", "8": "010101010101010", "9": "010101011001110", "-": "000000111000000", "/": "001001010100100", ".": "000000000000010", ":": "000010000010000", ">": "100010001010100", "<": "001010100010001", "+": "000010111010000", "%": "101001010100101", " ": "000000000000000", x: "000101010101000", "^": "010101000000000", v: "000000101010000" };
const tw = s => s.length * 4 - 1;
function txt(ctx, s, x, y, col) { ctx.fillStyle = col; s = String(s); for (let i = 0; i < s.length; i++) { const ch = s[i]; const g = F[ch] || F[ch.toUpperCase()] || F[' ']; for (let j = 0; j < 15; j++) if (g[j] === '1') ctx.fillRect(x + i * 4 + (j % 3), y + ((j / 3) | 0), 1, 1); } }

// ---------- helpers ----------
function shade(h, d) { const c = rgb(h).map(v => Math.max(0, Math.min(255, v + d))); return '#' + c.map(v => v.toString(16).padStart(2, '0')).join(''); }
function rng(seed) { return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const R = (ctx, x, y, w, h, c) => { ctx.fillStyle = c; ctx.fillRect(x, y, w, h); };
const cx = c => 7 + c * 18, cy = r => 17 + r * 18;
function bevel(ctx, x, y, w, h, f, hi, lo) { R(ctx, x, y, w, h, f); R(ctx, x, y, w, 1, hi); R(ctx, x, y, 1, h, hi); R(ctx, x, y + h - 1, w, 1, lo); R(ctx, x + w - 1, y, 1, h, lo); }
function inset(ctx, x, y, w, h, f, hi, lo) { R(ctx, x, y, w, h, f); R(ctx, x, y, w, 1, lo); R(ctx, x, y, 1, h, lo); R(ctx, x, y + h - 1, w, 1, hi); R(ctx, x + w - 1, y, 1, h, hi); }
function drawPin(ctx, x, y, over) {
  for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) { const ch = PIN[r][c]; if (ch === '.') continue; ctx.fillStyle = over[ch] || PIN_PAL[ch]; ctx.fillRect(x + c * 2, y + r * 2, 2, 2); }
}

function chassis(ctx, W, H, S, acc, seed, skinKey) {
  const rnd = rng(seed); const b = rgb(S.base);
  for (let y = 0; y < H; y++) { const row = (rnd() - .5) * 6; for (let x = 0; x < W; x++) { const n = row + (rnd() - .5) * 5; const i = (y * W + x) * 4; ctx.data[i] = b[0] + n; ctx.data[i + 1] = b[1] + n; ctx.data[i + 2] = b[2] + n; ctx.data[i + 3] = 255; } }
  for (let x = 0; x < W; x++) for (let y = 0; y < H; y++) {
    const corner = (Math.min(x, W - 1 - x) < 3 && Math.min(y, H - 1 - y) < 3) && (Math.min(x, W - 1 - x) + Math.min(y, H - 1 - y) < 3);
    if (corner) ctx.clearRect(x, y, 1, 1);
  }
  R(ctx, 3, 0, W - 6, 1, S.rim); R(ctx, 3, H - 1, W - 6, 1, S.rim); R(ctx, 0, 3, 1, H - 6, S.rim); R(ctx, W - 1, 3, 1, H - 6, S.rim);
  R(ctx, 1, 1, 2, 2, S.rim); R(ctx, W - 3, 1, 2, 2, S.rim); R(ctx, 1, H - 3, 2, 2, S.rim); R(ctx, W - 3, H - 3, 2, 2, S.rim);
  R(ctx, 3, 1, W - 6, 2, S.hi); R(ctx, 1, 3, 2, H - 6, S.hi); R(ctx, 3, H - 3, W - 6, 2, S.lo); R(ctx, W - 3, 3, 2, H - 6, S.lo);
  if (skinKey === 'guide') {
    R(ctx, 3, 3, W - 6, 2, S.leather); R(ctx, 3, H - 5, W - 6, 2, S.leather); R(ctx, 3, 3, 2, H - 6, S.leather); R(ctx, W - 5, 3, 2, H - 6, S.leather);
    for (let x = 6; x < W - 6; x += 3) { R(ctx, x, 4, 1, 1, S.leatherHi); R(ctx, x, H - 4, 1, 1, S.leatherHi); }
    for (let y = 6; y < H - 6; y += 3) { R(ctx, 4, y, 1, 1, S.leatherHi); R(ctx, W - 4, y, 1, 1, S.leatherHi); }
  }
}
function rivets(ctx, x, y, w, h, S) { [[x + 2, y + 2], [x + w - 4, y + 2], [x + 2, y + h - 4], [x + w - 4, y + h - 4]].forEach(([a, b]) => { R(ctx, a, b, 2, 2, S.plateLo); R(ctx, a, b, 1, 1, S.plateHi); }); }
function cellRect(c0, r0, c1, r1) { return [cx(c0), cy(r0), (c1 - c0 + 1) * 18, (r1 - r0 + 1) * 18]; }

function drawDecor(ctx, v, S, acc, skinKey, topH) {
  for (const d of v.decor || []) {
    if (d.t === 'bay') {
      let [x, y, w, h] = cellRect(d.c0, d.r0, d.c1, d.r1); x -= 1; y -= 1; w += 2; h += 2; x = Math.max(x, 5); w = Math.min(w, 171 - x);
      if (d.sheet) { inset(ctx, x, y, w, h, shade(S.base, 10), S.hi, S.lo); }
      else if (d.blueprint) { inset(ctx, x, y, w, h, '#2d4f7a', '#5b85b8', '#16283f'); ctx.fillStyle = '#3d6694'; for (let gx = x + 1; gx < x + w - 1; gx += 6) ctx.fillRect(gx, y + 1, 1, h - 2); for (let gy = y + 1; gy < y + h - 1; gy += 6) ctx.fillRect(x + 1, gy, w - 2, 1); }
      else { inset(ctx, x, y, w, h, S.bay, S.bayHi, S.bayLo); if (d.trim) { R(ctx, x, y - 1, w, 1, ACC.admin); R(ctx, x, y + h, w, 1, shade(ACC.admin, -60)); } }
    }
    else if (d.t === 'plate') {
      const [x, y, w, h] = cellRect(d.c0, d.r0, d.c1, d.r1); const px = x + 1, py = y + 1, pw = w - 2, ph = h - 2;
      bevel(ctx, px, py, pw, ph, S.plate, S.plateHi, S.plateLo); plateFx(ctx, d, px, py, pw, ph, S, acc, skinKey);
      if (d.text && d.pattern !== 'grid') { const tx = d.align === 'right' ? px + pw - 4 - tw(d.text) : px + 4; txt(ctx, d.text, tx, py + Math.floor((ph - 5) / 2), S.ink); }
    }
    else if (d.t === 'rail') {
      const n = d.text.length; const top = cy(d.r0), hh = (d.r1 - d.r0 + 1) * 18; const y0 = top + Math.floor((hh - (n * 6 - 1)) / 2);
      R(ctx, cx(d.c) + 3, top + 2, 12, hh - 4, shade(S.base, -14)); R(ctx, cx(d.c) + 3, top + 2, 12, 1, S.lo); R(ctx, cx(d.c) + 3, top + hh - 3, 12, 1, S.hi);
      for (let i = 0; i < n; i++) txt(ctx, d.text[i], cx(d.c) + 7, y0 + i * 6, S.ink);
    }
    else if (d.t === 'shutter') {
      const [x, y, w, h] = cellRect(0, d.r0, 8, d.r1); inset(ctx, x - 1, y, w + 2, h, S.bay, S.bayHi, S.bayLo);
      ctx.fillStyle = S.hatch; for (let i = -h; i < w; i += 5) for (let j = 0; j < h - 2; j++) { const xx = x + i + j; if (xx > x && xx < x + w - 1) ctx.fillRect(xx, y + 1 + j, 1, 1); }
      for (let r = d.r0; r <= d.r1; r++) { const yy = cy(r) + 6; const t = 'UPGRADE TO UNLOCK'; R(ctx, x + (w - tw(t)) / 2 - 3 | 0, yy - 2, tw(t) + 6, 9, S.bay); txt(ctx, t, (x + (w - tw(t)) / 2) | 0, yy, S.bayInk); }
    }
    else if (d.t === 'lcd') {
      const x = cx(d.c0) + 1, y = cy(d.r) + 2, w = (d.c1 - d.c0 + 1) * 18 - 2, h = 14; inset(ctx, x, y, w, h, S.lcd, S.bayHi, S.bayLo);
      for (let sx = x + 10; sx < x + w - 3; sx += 4) R(ctx, sx, y + 4, 3, 6, S.lcdOff); R(ctx, x + 3, y + 5, 4, 4, S.lcdOff);
    }
    else if (d.t === 'gap') { const t = d.text; const x = Math.round(8 + d.c * 18 + 8 - tw(t) / 2); txt(ctx, t, x, topH + 2, S.ink); }
    else if (d.t === 'bolt') { const x = cx(d.c), y = cy(d.r); bevel(ctx, x + 1, y + 1, 16, 16, S.plate, S.plateHi, S.plateLo); rivets(ctx, x + 1, y + 1, 16, 16, S); ctx.fillStyle = S.plateLo; for (let i = 0; i < 10; i++) ctx.fillRect(x + 4 + i, y + 4 + i, 1, 1); }
    else if (d.t === 'label') { const [x, y, w] = cellRect(d.c0, d.r, d.c1, d.r); txt(ctx, d.text, x + Math.floor((w - tw(d.text)) / 2), y + 7, (skinKey === 'guide' || d.tone === 'ink') ? S.ink : S.bayInk); }
    else if (d.t === 'emblem') {
      const [x, y, w, h] = cellRect(d.c0, d.r0, d.c1, d.r1);
      R(ctx, x, y, w, h, S.leather);
      R(ctx, x, y, w, 1, S.leatherLo); R(ctx, x, y + h - 1, w, 1, S.leatherLo); R(ctx, x, y, 1, h, S.leatherLo); R(ctx, x + w - 1, y, 1, h, S.leatherLo);
      R(ctx, x + 1, y + 1, w - 2, 1, S.leatherHi); R(ctx, x + 1, y + 1, 1, h - 2, S.leatherHi);
      R(ctx, x + 1, y + h - 2, w - 2, 1, S.leatherHi); R(ctx, x + w - 2, y + 1, 1, h - 2, S.leatherHi);
      for (const [px, py, dx, dy] of [[x, y, 1, 1], [x + w - 1, y, -1, 1], [x, y + h - 1, 1, -1], [x + w - 1, y + h - 1, -1, -1]]) {
        for (let i = 0; i < 3; i++) { R(ctx, px + dx * i, py, 1, 1, '#a0442c'); R(ctx, px, py + dy * i, 1, 1, '#a0442c'); }
      }
    }
    else if (d.t === 'tabtrack') { const a = d.c0 ?? 0, b = d.c1 ?? 8; if (d.c0 === undefined) R(ctx, 6, cy(d.r) + 15, 164, 3, shade(S.base, -30)); else R(ctx, cx(a) - 1, cy(d.r) + 15, (b - a + 1) * 18 + 2, 3, shade(S.base, -30)); }
    else if (d.t === 'chapters') {
      spec.chapter_tiles.tiles.forEach((t, i) => {
        const c0 = (i % 3) * 3, r0 = 1 + ((i / 3) | 0) * 2, x = cx(c0) + 1, y = cy(r0) + 1, w = 52, h = 34;
        bevel(ctx, x, y, w, h, '#ecdfb9', '#fbf3dc', '#9b814d');
        inset(ctx, x + 16, y + 2, 20, 20, S.leather, S.leatherHi, S.leatherLo);
        drawGrid(ctx, artOf(CHAPTER_ART[t.icon]), x + 18, y + 4);
        txt(ctx, t.label, x + ((w - tw(t.label)) / 2 | 0), y + 25, S.ink);
        R(ctx, x + 3, y + h - 3, w - 6, 1, ACC.guide);
      });
    }
    else if (d.t === 'arrow') { const x = cx(d.c), y = cy(d.r); const len = d.long ? 28 : 14; ctx.fillStyle = S.ink; ctx.fillRect(x + 2, y + 8, len - 4, 2); for (let i = 0; i < 5; i++) ctx.fillRect(x + len - 6 + i, y + 4 + i, 1, 10 - 2 * i); }
    else if (d.t === 'result') { const x = cx(d.c) - 4, y = cy(d.r) - 4; inset(ctx, x, y, 26, 26, S.sock, S.sockHi, S.sockLo); R(ctx, x - 1, y - 1, 28, 1, acc); R(ctx, x - 1, y + 26, 28, 1, acc); R(ctx, x - 1, y - 1, 1, 28, acc); R(ctx, x + 26, y - 1, 1, 28, acc); }
    else throw new Error('unknown decor op ' + d.t);
  }
}
function plateFx(ctx, d, x, y, w, h, S, acc, skinKey) {
  const p = d.pattern;
  if (p === 'chevron') { ctx.fillStyle = acc; const step = 8; for (let i = 4; i < w - 6; i += step) { for (let j = 0; j < 5; j++) { const xx = d.flip ? x + w - i - j - 1 : x + i + j; ctx.fillRect(xx, y + 3 + j, 2, 1); ctx.fillRect(xx, y + h - 4 - j, 2, 1); } } }
  else if (p === 'hazard') { for (let j = 2; j < h - 2; j++) for (let i = 2; i < w - 2; i++) { if (((i + j) >> 2) % 2 === 0) R(ctx, x + i, y + j, 1, 1, acc); else R(ctx, x + i, y + j, 1, 1, '#22241f'); } }
  else if (p === 'vent') { for (let j = 4; j < h - 3; j += 3) R(ctx, x + 5, y + j, w - 10, 1, S.plateLo); }
  else if (p === 'grain') { R(ctx, x + 1, y + 1, w - 2, h - 2, '#a06c3c'); for (let j = 2; j < h - 1; j += 3) R(ctx, x + 1, y + j, w - 2, 1, '#7e5129'); for (let i = 6; i < w; i += 23) R(ctx, x + i, y + 1, 1, h - 2, '#5e3b1c'); }
  else if (p === 'saw') { R(ctx, x + 1, y + 1, w - 2, h - 2, '#a06c3c'); for (let j = 3; j < h; j += 3) R(ctx, x + 1, y + j, w - 2, 1, '#7e5129'); ctx.fillStyle = '#d6d9dc'; for (let i = 2; i < w - 4; i += 6) { for (let k = 0; k < 4; k++) ctx.fillRect(x + i + k, y + h - 2 - k, 1, k + 1); } }
  else if (p === 'rune') { R(ctx, x + 1, y + 1, w - 2, h - 2, '#2b1f3a'); ctx.fillStyle = ACC.arcane; for (let i = 4; i < w - 4; i += 9) { ctx.fillRect(x + i, y + 4, 1, h - 8); ctx.fillRect(x + i - 2, y + 6, 5, 1); ctx.fillRect(x + i + 2, y + h - 7, 2, 1); } if (d.r0 === 0) txt(ctx, 'RITUALS', x + (w - tw('RITUALS')) / 2 | 0, y + 6, '#d9b8ff'); }
  else if (p === 'grid') { R(ctx, x + 1, y + 1, w - 2, h - 2, '#2d4f7a'); ctx.fillStyle = '#3d6694'; for (let i = x + 2; i < x + w - 1; i += 4) ctx.fillRect(i, y + 1, 1, h - 2); for (let j = y + 2; j < y + h - 1; j += 4) ctx.fillRect(x + 1, j, w - 2, 1); if (d.text) { R(ctx, x + 3, y + 4, tw(d.text) + 4, 9, '#2d4f7a'); txt(ctx, d.text, x + 5, y + 6, '#d7e6ff'); } }
  else if (p === 'crest') { R(ctx, x + w - 14, y + 3, 9, 10, ACC.admin); R(ctx, x + w - 13, y + 4, 7, 7, '#2f4a86'); R(ctx, x + w - 11, y + 6, 3, 3, ACC.admin); R(ctx, x + 2, y + h - 3, w - 4, 1, ACC.admin); }
  else if (p === 'seal') { R(ctx, x + 2, y + h / 2 | 0, w - 4, 1, S.plateLo); const m = x + w / 2 | 0; R(ctx, m - 5, y + 3, 10, 10, '#7a1f1f'); R(ctx, m - 4, y + 4, 8, 8, '#a83232'); R(ctx, m - 2, y + 6, 4, 4, ACC.admin); }
  else if (p === 'ribbon') { const m = x + w / 2 | 0; R(ctx, m - 4, y, 8, h + 4, '#a0442c'); R(ctx, m - 4, y, 8, 1, '#c46a4c'); for (let i = 0; i < 4; i++) ctx.clearRect(m - 4 + i, y + h + 3 - i, 8 - 2 * i, 1); }
  else if (p !== undefined) throw new Error('unknown plate pattern ' + p);
  if (skinKey !== 'guide' && !['grain', 'saw', 'rune', 'grid', 'hazard'].includes(p) && w > 30) rivets(ctx, x, y, w, h, S);
}
function socket(ctx, x, y, S, style, acc, rim) {
  inset(ctx, x, y, 18, 18, S.sock, S.sockHi, S.sockLo);
  if (rim) { R(ctx, x, y, 18, 1, rim); R(ctx, x, y, 1, 18, rim); }
  if (style === 'hot') { R(ctx, x, y + 17, 18, 1, acc); R(ctx, x + 17, y, 1, 18, acc); R(ctx, x, y, 18, 1, acc); R(ctx, x, y, 1, 18, acc); }
}
function playerInv(ctx, topH, S) {
  const y0 = topH + 13;
  inset(ctx, 6, y0 - 2, 164, 58, shade(S.base, -8), S.hi, S.lo); inset(ctx, 6, y0 + 56, 164, 22, shade(S.base, -8), S.hi, S.lo);
  for (let r = 0; r < 3; r++) for (let c = 0; c < 9; c++) inset(ctx, 7 + c * 18, y0 + r * 18, 18, 18, shade(S.base, -28), shade(S.base, 18), shade(S.base, -70));
  for (let c = 0; c < 9; c++) inset(ctx, 7 + c * 18, y0 + 58, 18, 18, shade(S.base, -28), shade(S.base, 18), shade(S.base, -70));
}

function renderChest(v, seed) {
  const skinKey = v.skin, S = SKINS[skinKey], acc = ACC[v.accent];
  if (!S || !acc) throw new Error('bad skin/accent for ' + v.id);
  const topH = 17 + v.rows * 18, W = 176, H = topH + 97;
  if (v.size[0] !== W || v.size[1] !== H) throw new Error('size mismatch for ' + v.id);
  const ctx = new Canvas(W, H);
  chassis(ctx, W, H, S, acc, seed, skinKey);
  R(ctx, 7, 14, 162, 1, acc); R(ctx, 7, 15, 162, 1, shade(acc, -50));
  drawDecor(ctx, v, S, acc, skinKey, topH);
  v.grid.forEach((row, r) => {
    for (let c = 0; c < 9; c++) {
      const ch = row[c], x = cx(c), y = cy(r);
      if (ch === '.') continue;
      if (ch === 'S') socket(ctx, x, y, S, 'norm', acc);
      else if (ch === 'H') socket(ctx, x, y, S, 'hot', acc);
      else if (RIM[ch]) socket(ctx, x, y, S, 'norm', acc, RIM[ch]);
      else if (ch === 'P') {
        socket(ctx, x, y, S, 'norm', acc);
        ctx.fillStyle = ACC.admin; for (let i = 0; i < 14; i += 2) { ctx.fillRect(x + 2 + i, y + 2, 1, 1); ctx.fillRect(x + 2 + i, y + 15, 1, 1); ctx.fillRect(x + 2, y + 2 + i, 1, 1); ctx.fillRect(x + 15, y + 2 + i, 1, 1); }
        drawPin(ctx, x + 1, y + 1, { r: shade(S.sock, 22), w: shade(S.sock, 30), d: shade(S.sock, 15) });
      } else throw new Error(`bad grid char '${ch}' in ${v.id}`);
    }
  });
  // tabtrack accent notches: drawn after sockets so they stay visible on the strip
  for (const d of v.decor) if (d.t === 'tabtrack') for (let c = d.c0 ?? 0; c <= (d.c1 ?? 8); c++) if (v.grid[d.r][c] !== '.') R(ctx, cx(c) + 6, cy(d.r) + 16, 6, 2, acc);
  playerInv(ctx, topH, S);
  return ctx;
}
function renderAnvil(v, seed) {
  const skinKey = v.skin, S = SKINS[skinKey], acc = ACC[v.accent];
  const W = 176, H = 166; const ctx = new Canvas(W, H);
  chassis(ctx, W, H, S, acc, seed, skinKey); R(ctx, 7, 14, 162, 1, acc); R(ctx, 7, 15, 162, 1, shade(acc, -50));
  const badge = skinKey === 'guide' ? 'INDEX' : 'TOWN';
  bevel(ctx, 10, 18, 42, 22, S.plate, S.plateHi, S.plateLo); txt(ctx, badge, 10 + (42 - tw(badge)) / 2 | 0, 22, S.ink);
  R(ctx, 14, 30, 34, 6, acc); R(ctx, 15, 31, 32, 4, shade(acc, -40));
  inset(ctx, 57, 18, 114, 20, S.bay, S.bayHi, S.bayLo); R(ctx, 58, 37, 112, 1, acc);
  // Transparent window over the vanilla rename field (sprite at 59,20, 110x16): the title glyph
  // is drawn after the EditBox, so anything opaque here would cover the text being typed.
  ctx.clearRect(59, 20, 110, 16);
  inset(ctx, 22, 42, 140, 26, S.bay, S.bayHi, S.bayLo);
  for (const [x, y] of [[26, 46], [75, 46], [133, 46]]) socket(ctx, x, y, S, 'norm', acc);
  ctx.fillStyle = S.bayInk; ctx.fillRect(52, 54, 10, 2); ctx.fillRect(56, 50, 2, 10);
  ctx.fillRect(100, 54, 22, 2); for (let i = 0; i < 5; i++) ctx.fillRect(122 + i, 50 + i, 1, 10 - 2 * i);
  txt(ctx, 'CONFIRM', 142 - tw('CONFIRM') / 2 | 0, 70, S.ink);
  inset(ctx, 6, 81, 164, 58, shade(S.base, -8), S.hi, S.lo); inset(ctx, 6, 139, 164, 22, shade(S.base, -8), S.hi, S.lo);
  for (let r = 0; r < 3; r++) for (let c = 0; c < 9; c++) inset(ctx, 7 + c * 18, 82 + r * 18, 18, 18, shade(S.base, -28), shade(S.base, 18), shade(S.base, -70));
  for (let c = 0; c < 9; c++) inset(ctx, 7 + c * 18, 140, 18, 18, shade(S.base, -28), shade(S.base, 18), shade(S.base, -70));
  return ctx;
}

// ---------- overlays ----------
function solid(w, h, col) { const c = new Canvas(w, h); R(c, 0, 0, w, h, col); return c; }
function digit(ch, col) { const c = new Canvas(3, 10); c.fillStyle = col; const g = F[ch]; for (let j = 0; j < 15; j++) if (g[j] === '1') c.fillRect(j % 3, ((j / 3) | 0) * 2, 1, 2); return c; }

// ---------- main ----------
const cp = s => parseInt(s.replace(/^U\+/, ''), 16);
const esc = n => '\\u' + n.toString(16).toUpperCase().padStart(4, '0');
const providers = []; const used = new Map(); const files = new Set();
function emit(file, canvas, codepoint, ascent, height) {
  if (used.has(codepoint)) throw new Error(`duplicate codepoint ${esc(codepoint)}: ${used.get(codepoint)} / ${file}`);
  used.set(codepoint, file);
  if (files.has(file)) throw new Error('duplicate file ' + file); files.add(file);
  fs.writeFileSync(path.join(texDir, file + '.png'), canvas.png());
  providers.push(`    {"type":"bitmap","file":"sovereignmc:gui/skins/${file}.png","ascent":${ascent},"height":${height},"chars":["${esc(codepoint)}"]}`);
}
fs.mkdirSync(texDir, { recursive: true });
fs.mkdirSync(path.dirname(fontFile), { recursive: true });

for (const v of spec.skins) {
  const seed = cp(v.codepoint);
  const ctx = v.kind === 'anvil' ? renderAnvil(v, seed) : renderChest(v, seed);
  if (ctx.w !== v.size[0] || ctx.h !== v.size[1]) throw new Error('size mismatch ' + v.id);
  emit(v.id, ctx, seed, 13, ctx.h);
}
const ov = Object.fromEntries(spec.overlays.map(o => [o.id, o]));
const steelOn = SKINS.steel.lcdOn, guideOn = SKINS.guide.lcdOn;
emit('ov_seg_on', solid(3, 6, steelOn), cp(ov.seg_on.codepoint), ov.seg_on.ascent, 6);
emit('ov_lamp_on', solid(4, 4, steelOn), cp(ov.lamp_on.codepoint), ov.lamp_on.ascent, 4);
emit('ov_lamp_off', solid(4, 4, ov.lamp_off.colour), cp(ov.lamp_off.codepoint), ov.lamp_off.ascent, 4);
const DIG = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '/', '%'], DIGN = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'slash', 'percent'];
const bases = { row5: 0xE6D0, row3: 0xE6E0, row0: 0xE6F0, row5_guide: 0xE720 };
for (const set of ['row5', 'row3', 'row0', 'row5_guide']) {
  const o = ov['digits_' + set];
  if (cp(o.codepoints.split('..')[0]) !== bases[set]) throw new Error('digit base mismatch ' + set);
  DIG.forEach((ch, i) => emit(`ov_digit_${DIGN[i]}_${set}`, digit(ch, set === 'row0' || set === 'row5_guide' ? guideOn : steelOn), bases[set] + i, o.ascent, 10));
}

// ---------- emblems (copied from SovereignPlates logos) + guide item icons ----------
const plateDir = path.join(root, 'assets/sovereignmc/textures/font/plate');
const logos = {};
for (const g of spec.emblems.glyphs) {
  const src = decodePng(fs.readFileSync(path.join(plateDir, `struct_${g.family}.png`)));
  if (src.w !== 32 || src.h !== 48) throw new Error('unexpected plate size ' + g.family);
  const c = new Canvas(32, 32); c.data.set(src.data.subarray(0, 32 * 32 * 4)); logos[g.family] = c;
  emit(g.file, c, cp(g.codepoint), spec.emblems.ascent, spec.emblems.height);
}
const itemTex = path.join(root, 'assets/sovereignmc/textures/item/guide');
const itemMdl = path.join(root, 'assets/sovereignmc/models/item/guide');
const itemDef = path.join(root, 'assets/sovereignmc/items/guide');
for (const d of [itemTex, itemMdl, itemDef]) fs.mkdirSync(d, { recursive: true });
for (const fam of spec.item_icons.families) {
  const big = logos[fam]; if (!big) throw new Error('no emblem for ' + fam);
  const ic = new Canvas(16, 16);
  for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) { const k = (y * 2 * 32 + x * 2) * 4; ic.data.set(big.data.subarray(k, k + 4), (y * 16 + x) * 4); }
  fs.writeFileSync(path.join(itemTex, `struct_${fam}.png`), ic.png());
  fs.writeFileSync(path.join(itemMdl, `struct_${fam}.json`), JSON.stringify({ parent: 'minecraft:item/generated', textures: { layer0: `sovereignmc:item/guide/struct_${fam}` } }, null, 2) + '\n');
  fs.writeFileSync(path.join(itemDef, `struct_${fam}.json`), JSON.stringify({ model: { type: 'minecraft:model', model: `sovereignmc:item/guide/struct_${fam}` } }, null, 2) + '\n');
}

// ---------- control icons ----------
const uiTex = path.join(root, 'assets/sovereignmc/textures/item/ui');
const uiMdl = path.join(root, 'assets/sovereignmc/models/item/ui');
const uiDef = path.join(root, 'assets/sovereignmc/items/ui');
for (const d of [uiTex, uiMdl, uiDef]) fs.mkdirSync(d, { recursive: true });
const jw = (f, o) => fs.writeFileSync(f, JSON.stringify(o, null, 2) + '\n');
const modelRef = n => ({ type: 'minecraft:model', model: `sovereignmc:item/ui/${n}` });
function icon16(artSpec) { const c = new Canvas(16, 16); drawGrid(c, artOf(artSpec), 0, 0); return c; }
for (const [id, art, states] of CONTROLS) {
  const names = states ? states.map((_, i) => `${id}_${i}`) : [id];
  (states || [art]).forEach((a, i) => {
    fs.writeFileSync(path.join(uiTex, names[i] + '.png'), icon16(a).png());
    jw(path.join(uiMdl, names[i] + '.json'), { parent: 'minecraft:item/generated', textures: { layer0: `sovereignmc:item/ui/${names[i]}` } });
  });
  if (!states) jw(path.join(uiDef, id + '.json'), { model: modelRef(id) });
  else jw(path.join(uiDef, id + '.json'), { model: { type: 'minecraft:range_dispatch', property: 'minecraft:custom_model_data', index: 0, entries: names.slice(1).map((n, i) => ({ threshold: i + 1, model: modelRef(n) })), fallback: modelRef(names[0]) } });
}
fs.writeFileSync(fontFile, '{\n  "providers": [\n' + providers.join(',\n') + '\n  ]\n}\n');
console.log(`wrote ${files.size} textures and ${path.relative(root, fontFile)}`);
