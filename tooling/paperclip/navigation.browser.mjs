import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { chromium } from '../../projects/trader/foundation_v2/web/node_modules/playwright/index.mjs'
import services from '../../projects/trader/foundation_v2/local-services.json' with { type: 'json' }

// Read-only against the owned local instance; drafts are never submitted.
const host = `http://${services.host}:${services.aiPreviewPort}`
const native = `http://${services.host}:${services.paperclipPort}`
const out = new URL('../../.runtime/research/paperclip-navigation/', import.meta.url)
await mkdir(out, { recursive: true })
const report = { cases: [], documentRequests: [], reloads: [], errors: [], blocked: [] }
const browser = await chromium.launch({ headless: true })
try {
  const context = await browser.newContext({ viewport: { width: 1920, height: 940 }, reducedMotion: 'reduce' })
  await context.addInitScript(() => {
    localStorage.setItem('tw-language', 'vi')
    localStorage.setItem('tw-shell-rail-collapsed', 'false')
    window.__paperclipDocumentId = crypto.randomUUID()
  })
  await context.route('**/*', route => {
    const request = route.request(), url = new URL(request.url())
    if (![host, native].includes(url.origin) || !['GET', 'HEAD'].includes(request.method())) {
      report.blocked.push({ method: request.method(), path: url.origin + url.pathname })
      return route.abort()
    }
    return route.continue()
  })
  const page = await context.newPage()
  page.setDefaultTimeout(15000)
  page.on('pageerror', error => report.errors.push(error.message))
  page.on('request', request => {
    if (request.isNavigationRequest()) report.documentRequests.push(request.url())
    if (request.url().includes('/@vite/client')) report.reloads.push('Vite client loaded')
  })
  page.on('websocket', socket => {
    if (new URL(socket.url()).port === String(services.paperclipHmrPort)) report.reloads.push('HMR connection opened')
  })
  await page.goto(`${host}/?workspace=tenant-a&view=ai&area=ai&section=paperclip&lang=vi`)
  const iframe = page.locator('iframe[title$="Paperclip"]')
  const element = await iframe.elementHandle()
  const frame = await element.contentFrame()
  const empty = frame.getByText('Không có công việc phù hợp với bộ lọc hoặc từ khóa.', { exact: true })
  await empty.waitFor({ timeout: 45000 })
  const documentId = await frame.evaluate(() => window.__paperclipDocumentId)
  const initialRequests = report.documentRequests.length
  async function unchanged(label) {
    assert.equal(await element.evaluate(node => node === document.querySelector('iframe[title$="Paperclip"]')), true, `${label}: iframe preserved`)
    assert.equal(await frame.evaluate(() => window.__paperclipDocumentId), documentId, `${label}: document preserved`)
    assert.equal(report.documentRequests.length, initialRequests, `${label}: no document reload`)
  }
  async function navigate(suffix) {
    await frame.locator(`a[href$="${suffix}"]`).filter({ visible: true }).first().click()
    await frame.waitForURL(url => url.pathname.endsWith(suffix === '/agents' ? '/agents/all' : suffix))
    // Allow delayed lazy overlays and agent-query settlement to become observable.
    await frame.locator('main').getByText('Đang tải…', { exact: true }).waitFor({ state: 'hidden' })
    await page.waitForTimeout(700)
    assert.equal(await frame.getByTestId('onboarding-wizard').count(), 0, `${suffix}: no automatic setup takeover`)
    await unchanged(suffix)
  }
  for (const suffix of ['/projects', '/skills', '/agents', '/dashboard', '/issues', '/dashboard', '/issues']) await navigate(suffix)
  report.cases.push('Native sidebar navigation, including repeated dashboard visits with zero agents')

  const search = frame.getByRole('textbox', { name: 'Tìm công việc', exact: true })
  await search.fill('navigation-regression-draft')
  await empty.locator('..').getByRole('button', { name: 'Tạo công việc', exact: true }).click()
  const dialog = frame.getByRole('dialog')
  const draft = dialog.locator('[contenteditable="true"]').first()
  await draft.fill('Giữ bản nháp khi chuyển công cụ và chờ làm việc')
  for (let i = 0; i < 3; i++) {
    await page.locator('.fx-subnav a[href*="section=connections"]').click()
    assert.equal(await iframe.isVisible(), false)
    await page.locator('.fx-subnav a[href*="section=paperclip"]').click()
    assert.equal(await draft.innerText(), 'Giữ bản nháp khi chuyển công cụ và chờ làm việc')
    await unchanged(`host tab cycle ${i + 1}`)
  }
  await page.getByTestId('language-toggle').click()
  await frame.getByRole('dialog', { name: 'New task', exact: true }).waitFor()
  await page.getByTestId('language-toggle').click()
  await frame.getByRole('dialog', { name: 'Tạo công việc', exact: true }).waitFor()
  await page.waitForTimeout(35000)
  await unchanged('idle with open draft')
  assert.equal(await draft.innerText(), 'Giữ bản nháp khi chuyển công cụ và chờ làm việc')
  await draft.press('Escape')
  await dialog.waitFor({ state: 'hidden' })
  assert.equal(await search.inputValue(), 'navigation-regression-draft')
  report.cases.push('Draft and search survive three host tab cycles, VI/EN switches and 35 seconds idle')

  await navigate('/dashboard')
  await frame.getByRole('button', { name: 'Tạo một agent ở đây', exact: true }).click()
  await frame.getByTestId('onboarding-wizard').waitFor()
  await unchanged('explicit native setup')
  report.cases.push('Explicit native create-agent action still opens onboarding')
  assert.deepEqual(report.reloads, [])
  assert.deepEqual(report.errors, [])
  assert.deepEqual(report.blocked, [])
  report.status = 'pass'
} catch (error) {
  report.status = 'fail'
  report.failure = error.stack
  process.exitCode = 1
} finally {
  await writeFile(new URL('report.json', out), JSON.stringify(report, null, 2))
  console.log(JSON.stringify(report, null, 2))
  await browser.close()
}
