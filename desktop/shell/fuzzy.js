/* Vixzen fuzzy matcher v1.0 — pure JavaScript, no GNOME imports.
 *
 * Deliberately dependency-free so the same module powers:
 *   - the Vixzen Palette (desktop/shell/palette.js)
 *   - the Start Menu search (desktop/shell/extension.js)
 *   - the offline test suite (tests/js/fuzzy_smoke.js via gjs -m)
 *
 * Scoring model (higher = better):
 *   +6  match at start of string
 *   +4  match at a word boundary (space - _ . /)
 *   +3  consecutive with previous matched char
 *   +12 exact full-string match
 *   +5  prefix of the whole string
 *   -0.05 per target char (prefers short names)
 * Returns null when there is no match, 0 for an empty query.
 */

const BOUNDARY = new Set([' ', '-', '_', '.', '/']);

function _walk(query, target) {
    if (typeof query !== 'string' || typeof target !== 'string')
        return null;
    const q = query.toLowerCase();
    const t = target.toLowerCase();
    if (q.length === 0)
        return [];
    if (q.length > t.length)
        return null;

    const indices = [];
    let ti = 0;
    for (let qi = 0; qi < q.length; qi++) {
        const c = q[qi];
        let found = -1;
        for (let j = ti; j < t.length; j++) {
            if (t[j] === c) { found = j; break; }
        }
        if (found < 0)
            return null;
        indices.push(found);
        ti = found + 1;
    }
    return indices;
}

export function fuzzyScore(query, target) {
    const indices = _walk(query, target);
    if (indices === null)
        return null;
    if (indices.length === 0)
        return 0;

    const q = query.toLowerCase();
    const t = target.toLowerCase();
    let score = 0;
    let prev = -1;
    for (const i of indices) {
        let pts = 1;
        if (i === 0)
            pts += 6;
        else if (BOUNDARY.has(t[i - 1]))
            pts += 4;
        if (prev >= 0 && i === prev + 1)
            pts += 3;
        score += pts;
        prev = i;
    }
    if (t === q)
        score += 12;
    if (t.startsWith(q))
        score += 5;
    score -= t.length * 0.05;
    return score;
}

export function matchIndices(query, target) {
    return _walk(query, target);
}

/* Escape text for Pango markup, then bold the matched characters. */
export function highlightedLabel(query, target) {
    const AMP = String.fromCharCode(38); // literal ampersand, un-mangleable
    const esc = (s) => s.replaceAll('&', AMP + 'amp;')
        .replaceAll('<', AMP + 'lt;')
        .replaceAll('>', AMP + 'gt;');
    const indices = _walk(query, target);
    if (indices === null || indices.length === 0)
        return esc(target);
    const set = new Set(indices);
    let out = '';
    for (let i = 0; i < target.length; i++) {
        const piece = esc(target[i]);
        out += set.has(i) ? `<b>${piece}</b>` : piece;
    }
    return out;
}
