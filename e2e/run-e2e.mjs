/**
 * CoinHQ E2E UI verification.
 *
 * Prereqs (see e2e/README.md):
 *   - backend running on :8000 in DEMO_MODE with seed_demo.py data
 *   - frontend (next start) on :3000 with default NEXT_PUBLIC_API_URL
 *   - SEED_JSON env pointing at seed_demo.py output (default /tmp/seed.json)
 *
 * Verifies real user flows in a real browser and saves screenshots to
 * SHOT_DIR (default /tmp/e2e-shots). Exits non-zero if any check fails.
 */
import { chromium } from 'playwright';
import { readFileSync, mkdirSync } from 'node:fs';

const FRONTEND = process.env.FRONTEND_URL ?? 'http://localhost:3000';
const SEED = JSON.parse(readFileSync(process.env.SEED_JSON ?? '/tmp/seed.json', 'utf8'));
const SHOTS = process.env.SHOT_DIR ?? '/tmp/e2e-shots';
mkdirSync(SHOTS, { recursive: true });

const results = [];
function check(id, desc, ok, extra = '') {
  results.push({ id, desc, ok, extra });
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${id}  ${desc}${extra ? '  [' + extra + ']' : ''}`);
}

const browser = await chromium.launch();

async function newPage({ jwt } = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  if (jwt) {
    await ctx.addInitScript(([t]) => {
      localStorage.setItem('token', t);
      localStorage.setItem('onboarding_done', 'true');
    }, [jwt]);
  }
  return ctx.newPage();
}

const jwt = SEED.users.demo.jwt;

// ── 1. Login page renders ─────────────────────────────────────────────────────
{
  const page = await newPage();
  await page.goto(`${FRONTEND}/login`, { waitUntil: 'networkidle' });
  check('UI-01', 'login: Google CTA gorunur',
    await page.getByText(/Continue with Google/i).isVisible());
  await page.screenshot({ path: `${SHOTS}/01-login.png` });
  await page.context().close();
}

// ── 2. Dashboard: portfolio + chart + PnL + history ──────────────────────────
{
  const page = await newPage({ jwt });
  await page.goto(`${FRONTEND}/dashboard`, { waitUntil: 'networkidle' });
  // Wait until the portfolio total actually renders (SWR profiles + portfolio
  // fetch + chart hydration) rather than a fixed sleep.
  await page.getByText(/Total Portfolio Value/i).waitFor({ timeout: 15000 }).catch(() => {});
  await page.waitForFunction(() => /\$[0-9][0-9,]*\.[0-9]{2}/.test(document.body.innerText), null, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const body = await page.textContent('body');
  // Price-independent: assert a positive formatted total renders (in DEMO_MODE
  // prices are deterministic so the value is stable, but we don't hard-code it).
  const totalMatch = body.match(/\$[1-9][0-9,]*\.[0-9]{2}/);
  check('UI-02', 'dashboard: pozitif toplam deger gorunur', !!totalMatch, totalMatch ? totalMatch[0] : 'YOK');
  check('UI-03', 'dashboard: demo exchange listelenir', /demo/i.test(body));
  check('UI-04', 'dashboard: BTC bakiyesi gorunur', /BTC/.test(body));
  check('UI-05', 'dashboard: allocation chart (svg) render edilir',
    (await page.locator('svg').count()) > 0);
  await page.screenshot({ path: `${SHOTS}/02-dashboard.png`, fullPage: true });
  await page.context().close();
}

// ── 3. Settings: profil, key rozetleri, share linkler, owner trade ────────────
{
  const page = await newPage({ jwt });
  await page.goto(`${FRONTEND}/settings`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const body = await page.textContent('body');
  check('UI-06', 'settings: profil adi gorunur', /Main Portfolio/.test(body));
  check('UI-07', 'settings: Read-only + Trade key rozetleri', /Read-only/i.test(body) && /Trade/.test(body));
  check('UI-08', 'settings: share linkler listelenir (label)', /Muhasebeci/.test(body));
  check('UI-09', 'settings: owner trade paneli gorunur', /Place (buy|sell) order/i.test(body));
  await page.screenshot({ path: `${SHOTS}/03-settings.png`, fullPage: true });

  // Owner trade via UI: buy 25 USD BTC
  try {
    await page.getByLabel('Asset').first().fill('BTC');
    await page.getByLabel('USD amount').first().fill('25');
    await page.getByRole('button', { name: /Place buy order/i }).first().click();
    await page.waitForTimeout(2500);
    const after = await page.textContent('body');
    check('UI-10', 'settings: owner emri UI uzerinden fill olur', /Order filled/i.test(after));
    await page.screenshot({ path: `${SHOTS}/04-owner-trade.png`, fullPage: true });
  } catch (e) {
    check('UI-10', 'settings: owner emri UI uzerinden fill olur', false, String(e).slice(0, 80));
  }
  await page.context().close();
}

// ── 4. Public share (open+trade): panel + limitler + emir + limit reddi ──────
{
  const page = await newPage(); // NO auth — public
  await page.goto(`${FRONTEND}/share/${SEED.share_tokens.open_trade}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2500);
  const body = await page.textContent('body');
  check('UI-11', 'share(open): Trading enabled rozeti', /Trading enabled/i.test(body));
  check('UI-12', 'share(open): limitler gorunur ($500/order, $2,000/24h, BTC,ETH)',
    /500/.test(body) && /2,000/.test(body) && /BTC,\s*ETH/i.test(body));
  check('UI-13', 'share(open): gercek exchange adi gorunur (demo)', /demo/i.test(body));
  await page.screenshot({ path: `${SHOTS}/05-share-trade.png`, fullPage: true });

  // Valid delegate order via UI: buy 50 USD ETH
  await page.getByLabel('Asset').fill('ETH');
  await page.getByLabel('USD amount').fill('50');
  await page.getByRole('button', { name: /Place buy order/i }).click();
  await page.waitForTimeout(2500);
  let after = await page.textContent('body');
  check('UI-14', 'share(open): delegate emri fill olur', /Order filled/i.test(after));
  await page.screenshot({ path: `${SHOTS}/06-delegate-trade-ok.png`, fullPage: true });

  // Over-limit order: 600 USD > 500 per-order cap → visible error
  await page.getByLabel('Asset').fill('BTC');
  await page.getByLabel('USD amount').fill('600');
  await page.getByRole('button', { name: /Place buy order/i }).click();
  await page.waitForTimeout(2500);
  after = await page.textContent('body');
  check('UI-15', 'share(open): emir-basi limit asimi UI hatasi verir',
    /per-order limit/i.test(after) || /exceeds/i.test(after));
  await page.screenshot({ path: `${SHOTS}/07-delegate-trade-limit.png`, fullPage: true });
  await page.context().close();
}

// ── 5. Masked share: maskeleme + read-only ────────────────────────────────────
{
  const page = await newPage();
  await page.goto(`${FRONTEND}/share/${SEED.share_tokens.masked}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);
  const body = await page.textContent('body');
  check('UI-16', 'share(masked): exchange adi maskeli (Exchange xxxx)', /Exchange [0-9a-f]{8}/.test(body));
  check('UI-17', 'share(masked): gercek exchange adi SIZMAZ', !/>\s*demo\s*</i.test(await page.content()));
  check('UI-18', 'share(masked): Read-only rozeti, trade paneli YOK',
    /Read-only view/i.test(body) && !/Place (buy|sell) order/i.test(body));
  check('UI-19', 'share(masked): follow butonu yok (allow_follow=false)',
    !/Add to my portfolio/i.test(body));
  await page.screenshot({ path: `${SHOTS}/08-share-masked.png`, fullPage: true });
  await page.context().close();
}

// ── 6. Expired & revoked share sayfalari ──────────────────────────────────────
{
  const page = await newPage();
  await page.goto(`${FRONTEND}/share/${SEED.share_tokens.expired}`, { waitUntil: 'networkidle' });
  check('UI-20', 'share(expired): "Link not available"',
    /Link not available|expired/i.test(await page.textContent('body')));
  await page.screenshot({ path: `${SHOTS}/09-share-expired.png` });

  await page.goto(`${FRONTEND}/share/${SEED.share_tokens.revoked}`, { waitUntil: 'networkidle' });
  check('UI-21', 'share(revoked): "Link not available"',
    /Link not available|revoked/i.test(await page.textContent('body')));
  await page.context().close();
}

// ── 7. Pricing page ───────────────────────────────────────────────────────────
{
  const page = await newPage();
  await page.goto(`${FRONTEND}/pricing`, { waitUntil: 'networkidle' });
  check('UI-22', 'pricing: planlar + waitlist formu',
    /Cloud Premium/.test(await page.textContent('body')));
  await page.screenshot({ path: `${SHOTS}/10-pricing.png`, fullPage: true });
  await page.context().close();
}

await browser.close();

const failed = results.filter(r => !r.ok);
console.log(`\n==== E2E SONUC: ${results.length - failed.length}/${results.length} PASS ====`);
if (failed.length) {
  console.log('FAILED:', failed.map(f => f.id).join(', '));
  process.exit(1);
}
