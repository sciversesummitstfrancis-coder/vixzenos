/* Vixzen fuzzy.js test harness — executed by `gjs -m` from pytest.
 * Imports the REAL module (no copy), runs ranking cases, prints JSON.
 * Exit code 0 = all assertions hold.
 */
import {fuzzyScore, highlightedLabel, matchIndices} from '../../desktop/shell/fuzzy.js';
import System from 'system';

const results = [];
function check(name, cond, detail = '') {
    results.push({ name, pass: !!cond, detail: String(detail) });
}

// 1. empty query scores 0 (matches everything, keeps provider order)
check('empty-query-0', fuzzyScore('', 'Anything') === 0);

// 2. impossible match returns null
check('no-match-null', fuzzyScore('zzz', 'Files') === null);

// 3. exact full match beats partial
const sExact = fuzzyScore('files', 'Files');
const sPartial = fuzzyScore('files', 'Files Manager');
check('exact-beats-partial', sExact !== null && sPartial !== null && sExact > sPartial, `${sExact} vs ${sPartial}`);

// 4. prefix beats scattered subsequence
const sPrefix = fuzzyScore('set', 'Settings');
const sScatter = fuzzyScore('set', 'System Settings');
check('prefix-beats-scattered', sPrefix !== null && sScatter !== null && sPrefix > sScatter, `${sPrefix} vs ${sScatter}`);

// 5. subsequence works (Flow-style abbreviations)
check('subsequence-match', fuzzyScore('vwm', 'Vixzen Web Menu') !== null);

// 6. case-insensitive
check('case-insensitive', fuzzyScore('VIX', 'Vixzen') !== null);

// 7. deterministic
check('deterministic', fuzzyScore('term', 'Terminal') === fuzzyScore('term', 'Terminal'));

// 8. word-boundary bonus exists ('web' in 'Vixzen Web' > 'web' mid-word)
const sBound = fuzzyScore('web', 'Vixzen Web');
const sMid = fuzzyScore('web', 'Unawebsite');
check('word-boundary-bonus', sBound !== null && sMid !== null && sBound > sMid, `${sBound} vs ${sMid}`);

// 9. matchIndices aligns with query
const idx = matchIndices('vwm', 'Vixzen Web Menu');
check('indices-valid', Array.isArray(idx) && idx.length === 3 &&
    'Vixzen Web Menu'[idx[0]].toLowerCase() === 'v' &&
    'Vixzen Web Menu'[idx[1]].toLowerCase() === 'w' &&
    'Vixzen Web Menu'[idx[2]].toLowerCase() === 'm', JSON.stringify(idx));

// 10. highlightedLabel bolds matches and escapes nothing dangerous
const hl = highlightedLabel('vix', 'Vixzen');
check('highlight-bold', hl.includes('<b>') && hl.startsWith('<b>V'), hl);
check('highlight-plain-when-null', highlightedLabel('zzz', 'Files') === 'Files');

// 11. performance: 200 candidates x 3 queries must stay under 50ms total
const names = [];
for (let i = 0; i < 200; i++) names.push(`App Number ${i} Of Many`);
const t0 = Date.now();
for (const q of ['app', 'num', 'vix'])
    for (const n of names) fuzzyScore(q, n);
const elapsed = Date.now() - t0;
check('benchmark-200x3-under-50ms', elapsed < 50, `${elapsed}ms`);

const failed = results.filter(r => !r.pass);
print(JSON.stringify({ results, failed: failed.length, elapsed_ms: elapsed }));
if (failed.length > 0) System.exit(1);
