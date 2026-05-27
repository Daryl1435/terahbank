/**
 * TerahBank Mobile UI Screenshot Script
 * Runs Expo web in a mobile viewport (iPhone 14 size) and snapshots every reachable screen.
 *
 * Screens that require auth data will still render their nav chrome + loading/error state —
 * good enough to verify layout, alignment, and typography.
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE_URL = 'http://localhost:19006';
const OUT_DIR  = path.resolve(__dirname, 'ui images');
const VIEWPORT = { width: 390, height: 844 };   // iPhone 14 logical pixels

if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

async function snap(page, name) {
  await page.waitForTimeout(1200);   // let animations settle
  const file = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  console.log(`  ✓  ${name}.png`);
}

async function waitForApp(page) {
  // Wait until the React app has mounted (root div has children)
  await page.waitForFunction(() => {
    const root = document.getElementById('root');
    return root && root.children.length > 0;
  }, { timeout: 15000 });
  await page.waitForTimeout(2000); // font + animation settle
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 2,    // retina quality
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
  });
  const page = await context.newPage();

  // Suppress console noise from native modules that don't work on web
  page.on('console', msg => {
    if (msg.type() === 'error') return;  // skip; expected for some native APIs
  });

  console.log('\n📱 TerahBank UI Screenshot Run\n' + '─'.repeat(40));

  // ── 1. Language picker (first-launch screen, shown before nav) ────────────
  console.log('\n[1/2] Auth & onboarding flow');
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await waitForApp(page);
  await snap(page, '00_language_picker');

  // Pick French to proceed
  try {
    // Look for the French button / touchable
    const frBtn = page.locator('text=Français').first();
    if (await frBtn.isVisible({ timeout: 3000 })) {
      await frBtn.click();
      await page.waitForTimeout(1500);
    }
  } catch (_) {}
  await snap(page, '01_login');

  // ── Navigate to Register ──────────────────────────────────────────────────
  try {
    const registerBtn = page.locator("text=S'inscrire, text=Créer un compte, text=Register").first();
    if (await registerBtn.isVisible({ timeout: 2000 })) {
      await registerBtn.click();
      await page.waitForTimeout(1000);
      await snap(page, '02_register');
      await page.goBack();
      await page.waitForTimeout(800);
    }
  } catch (_) {
    // Try clicking any "create account" link
    try {
      await page.click('text=créer', { timeout: 2000 });
      await page.waitForTimeout(1000);
      await snap(page, '02_register');
      await page.goBack();
    } catch (_2) {}
  }

  // ── Fill login form (won't actually authenticate — API offline) ───────────
  try {
    await page.fill('input[type="tel"], input[placeholder*="237"], input[placeholder*="phone"]', '+237600000000', { timeout: 2000 });
  } catch (_) {}
  try {
    await page.fill('input[type="password"]', 'Terah@12345', { timeout: 2000 });
    await snap(page, '03_login_filled');
  } catch (_) {}

  // ── 2. Attempt to reach OTP screen (shows if login fires) ────────────────
  // We won't get past OTP without real API — snap the login error state instead
  try {
    await page.click('button:has-text("Connexion"), button:has-text("Se connecter"), [role="button"]:has-text("Connexion")', { timeout: 2000 });
    await page.waitForTimeout(2000);
    await snap(page, '04_login_error_or_otp');
  } catch (_) {}

  // ── 3. Go back to clean login, then navigate to Password Creation ─────────
  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await waitForApp(page);

  // Skip language picker if it appears again
  try {
    const frBtn = page.locator('text=Français').first();
    if (await frBtn.isVisible({ timeout: 2000 })) {
      await frBtn.click();
      await page.waitForTimeout(1200);
    }
  } catch (_) {}

  // Navigate to registration flow to snap password creation, PIN setup, OTP screens
  console.log('\n[2/2] Registration sub-screens');
  try {
    await page.click('text=créer, text=Créer, text=Register, text=S\'inscrire', { timeout: 2000 });
    await page.waitForTimeout(1000);
    await snap(page, '05_register_fresh');

    // Fill phone
    await page.fill('input', '+237600000001', { timeout: 2000 });
    await page.waitForTimeout(500);
    await snap(page, '06_register_phone_filled');
  } catch (_) {}

  // ── 4. Reload fresh to capture each screen in isolation ──────────────────
  // Use hash/query tricks to reach screens via Expo Router style (won't work for native stack)
  // Instead: systematically interact to reach pre-auth screens

  await page.goto(BASE_URL, { waitUntil: 'networkidle' });
  await waitForApp(page);
  try {
    const frBtn = page.locator('text=Français').first();
    if (await frBtn.isVisible({ timeout: 2000 })) {
      await frBtn.click();
      await page.waitForTimeout(1500);
    }
  } catch (_) {}

  // Final login screen snap
  await snap(page, '07_login_final');

  // ── 5. Inject fake auth state into localStorage/sessionStorage ────────────
  // React Navigation stores nav state; we can inject auth state to skip login
  console.log('\n[Auth bypass] Injecting mock auth state…');
  await page.evaluate(() => {
    // Simulate Zustand auth store persistence — TerahBank uses SecureStore on native
    // but web falls back to localStorage
    try {
      localStorage.setItem('auth-storage', JSON.stringify({
        state: {
          userId: 'mock-user-123',
          fullName: 'Ama Ngala',
          isAuthenticated: true,
          kycStatus: 'approved',
        },
        version: 0,
      }));
      localStorage.setItem('app-storage', JSON.stringify({
        state: {
          language: 'fr',
          languageSelected: true,
          fontSize: 'medium',
          lastActiveAt: Date.now(),
        },
        version: 0,
      }));
    } catch (e) {}
  });

  await page.reload({ waitUntil: 'networkidle' });
  await waitForApp(page);
  await snap(page, '08_dashboard_or_kyc');

  // Give it more time for any async renders
  await page.waitForTimeout(2000);
  await snap(page, '09_dashboard_loaded');

  // ── 6. Try navigation buttons on dashboard ────────────────────────────────
  const navTargets = [
    { label: 'Dépôt',       name: '10_deposit' },
    { label: 'Retrait',     name: '11_withdraw' },
    { label: 'Virement',    name: '12_transfer' },
    { label: 'Mes cartes',  name: '13_cards' },
    { label: 'Assurance',   name: '14_insurance' },
  ];

  for (const { label, name } of navTargets) {
    try {
      // Go back to dashboard first
      const backBtn = page.locator('text=← Retour, text=← back, text=←').first();
      if (await backBtn.isVisible({ timeout: 1000 })) {
        await backBtn.click();
        await page.waitForTimeout(800);
      }
      // Try the button
      await page.click(`text=${label}`, { timeout: 2000 });
      await page.waitForTimeout(1500);
      await snap(page, name);
    } catch (_) {
      console.log(`  ⚠  Could not reach: ${label}`);
    }
  }

  // ── 7. Profile ────────────────────────────────────────────────────────────
  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await waitForApp(page);
    await page.evaluate(() => {
      try {
        localStorage.setItem('auth-storage', JSON.stringify({
          state: { userId: 'mock-user-123', fullName: 'Ama Ngala', isAuthenticated: true, kycStatus: 'approved' },
          version: 0,
        }));
        localStorage.setItem('app-storage', JSON.stringify({
          state: { language: 'fr', languageSelected: true, fontSize: 'medium', lastActiveAt: Date.now() },
          version: 0,
        }));
      } catch (e) {}
    });
    await page.reload({ waitUntil: 'networkidle' });
    await waitForApp(page);
    await page.waitForTimeout(1500);

    // Look for avatar / profile icon
    await page.click('[aria-label*="profil"], [aria-label*="profile"], [aria-label*="Profile"]', { timeout: 2000 });
    await page.waitForTimeout(1500);
    await snap(page, '15_profile');
  } catch (_) {
    console.log('  ⚠  Profile navigation skipped');
  }

  // ── 8. Notifications ─────────────────────────────────────────────────────
  try {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await waitForApp(page);
    await page.evaluate(() => {
      try {
        localStorage.setItem('auth-storage', JSON.stringify({
          state: { userId: 'mock-user-123', fullName: 'Ama Ngala', isAuthenticated: true, kycStatus: 'approved' },
          version: 0,
        }));
        localStorage.setItem('app-storage', JSON.stringify({
          state: { language: 'fr', languageSelected: true, fontSize: 'medium', lastActiveAt: Date.now() },
          version: 0,
        }));
      } catch (e) {}
    });
    await page.reload({ waitUntil: 'networkidle' });
    await waitForApp(page);
    await page.waitForTimeout(1500);

    await page.click('[aria-label*="notif"], [aria-label*="Notif"]', { timeout: 2000 });
    await page.waitForTimeout(1500);
    await snap(page, '16_notifications');
  } catch (_) {
    console.log('  ⚠  Notifications navigation skipped');
  }

  // ── Done ──────────────────────────────────────────────────────────────────
  await browser.close();

  const files = fs.readdirSync(OUT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\n✅ Done — ${files.length} screenshots saved to: ui images/\n`);
  files.forEach(f => console.log(`   ${f}`));
})();
