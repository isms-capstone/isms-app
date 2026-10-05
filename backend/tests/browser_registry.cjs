const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright');
const output = 'backend/tests/ui-output';
fs.mkdirSync(output, {recursive: true});

(async () => {
  const deadline = Date.now() + 15000;
  let ready = false;
  while (Date.now() < deadline) {
    try {
      const response = await fetch('http://127.0.0.1:8765/registry');
      if (response.ok) { ready = true; break; }
    } catch (_) { /* The isolated preview may still be starting. */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  if (!ready) throw new Error('Start the isolated QA server: python backend/tests/preview_registry.py');
  const browser = await chromium.launch({headless: true, ...(process.env.PLAYWRIGHT_CHANNEL ? {channel: process.env.PLAYWRIGHT_CHANNEL} : {})});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto('http://127.0.0.1:8765/registry');
    await page.getByLabel('ชื่อผู้ใช้', {exact: true}).fill('qa-admin');
    await page.getByLabel('รหัสผ่าน', {exact: true}).fill('test-only-password');
    await page.getByRole('button', {name: 'เข้าสู่ระบบ', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่มองค์กร', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มองค์กร', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('TU · คณะแพทยศาสตร์');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('button', {name: 'TU · คณะแพทยศาสตร์', exact: true}).waitFor();
    await page.getByRole('button', {name: 'Product Registry', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่มผลิตภัณฑ์', exact: true}).click();
    await page.locator('dialog').getByLabel('รหัส (a-z, 0-9, ขีดกลาง/ขีดล่าง)').fill('examplus');
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('ExamPlus');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('button', {name: 'ExamPlus', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่มโมดูล', exact: true}).click();
    await page.locator('dialog').getByLabel('รหัส (a-z, 0-9, ขีดกลาง/ขีดล่าง)').fill('teacher');
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('Teacher');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'Teacher', exact: true}).waitFor();
    await page.getByRole('button', {name: 'เลือกทีม', exact: true}).click();
    await page.locator('dialog').getByLabel('ทีม', {exact: true}).selectOption({label: 'Support'});
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.locator('#workspace').getByText('Support', {exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มอาการ', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่ออาการ', {exact: true}).fill('เข้าสู่ระบบไม่ได้');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'เข้าสู่ระบบไม่ได้', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มช่วงเวลาสอบ', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อช่วงเวลาสอบ', {exact: true}).fill('ระหว่างสอบจริง');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'ระหว่างสอบจริง', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มประเภทปัญหา', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อประเภทปัญหา', {exact: true}).fill('รหัสผ่าน');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'รหัสผ่าน', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ สร้างนโยบาย SLA', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อนโยบาย SLA', {exact: true}).fill('ExamPlus SLA');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่มกฎ SLA', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มกฎ SLA', exact: true}).click();
    await page.locator('dialog').getByLabel('เวลาตอบกลับ', {exact: true}).fill('15');
    await page.locator('dialog').getByLabel('เวลาปิดเคสต่ำสุด', {exact: true}).fill('1');
    await page.locator('dialog').getByLabel('เวลาปิดเคสสูงสุด', {exact: true}).fill('2');
    await page.locator('dialog').getByLabel('หน่วยเวลาปิดเคส', {exact: true}).selectOption('HOURS');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: '15 MINUTES', exact: true}).waitFor();
    // Current product settings are read from ADM on every request, without restart.
    const login = await fetch('http://127.0.0.1:8765/api/v1/auth/login', {method: 'POST', body: new URLSearchParams({username: 'qa-admin', password: 'test-only-password'})});
    const headers = {Authorization: `Bearer ${(await login.json()).access_token}`, 'Content-Type': 'application/json'};
    const api = async (path, init = {}) => {
      const response = await fetch(`http://127.0.0.1:8765/api/v1${path}`, {...init, headers});
      assert.equal(response.ok, true, await response.clone().text());
      return response.json();
    };
    const products = await api('/products');
    const exam = products.find(product => product.code === 'examplus');
    const options = await api(`/products/${exam.id}/case-options`);
    assert.equal(options.symptoms[0].name, 'เข้าสู่ระบบไม่ได้');
    assert.equal(options.sla_policy.rules[0].first_response_value, 15);
    const other = await api('/admin/master-data/products', {method: 'POST', body: JSON.stringify({name: 'Other Product QA'})});
    const otherOptions = await api(`/products/${other.id}/case-options`);
    assert.deepEqual(otherOptions.symptoms, []);
    assert.deepEqual(otherOptions.modules, []);
    assert.equal(otherOptions.sla_policy, null);
    await page.screenshot({path: path.join(output, 'registry-product-configuration.png'), fullPage: true});

    await page.getByRole('button', {name: 'Customers', exact: true}).click();
    await page.getByRole('button', {name: 'TU · คณะแพทยศาสตร์', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่มผู้ติดต่อ', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('อาจารย์สมชาย');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('button', {name: 'ช่องทางติดต่อ', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่มช่องทาง', exact: true}).click();
    await page.locator('dialog').getByLabel('ประเภทช่องทาง').selectOption('email');
    await page.locator('dialog').getByLabel('ข้อมูลช่องทาง').fill('teacher@example.org');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'teacher@example.org', exact: true}).waitFor();
    await page.getByRole('button', {name: '← กลับข้อมูลลูกค้า', exact: true}).click();
    await page.getByRole('button', {name: '+ เพิ่ม instance', exact: true}).click();
    await page.locator('dialog').getByLabel('ผลิตภัณฑ์', {exact: true}).selectOption({label: 'ExamPlus'});
    await page.locator('dialog').getByLabel('รหัส (a-z, 0-9, ขีดกลาง/ขีดล่าง)').fill('production');
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('TU ExamPlus');
    await page.locator('dialog').getByLabel('เวอร์ชัน', {exact: true}).fill('1.2.3');
    await page.locator('dialog').getByLabel('Environment', {exact: true}).fill('production');
    await page.locator('dialog').getByLabel('URL', {exact: true}).fill('https://exam.example.org');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'ExamPlus · TU ExamPlus', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มหน่วยงาน', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('ภาควิชาอายุรศาสตร์');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'ภาควิชาอายุรศาสตร์', exact: true}).waitFor();
    await page.getByRole('button', {name: '+ เพิ่มรายการ', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อ', {exact: true}).fill('MED101');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'MED101', exact: true}).waitFor();
    await page.getByRole('button', {name: 'แก้ไขสัญญา', exact: true}).click();
    await page.locator('dialog').getByLabel('วันเริ่มสัญญา').fill('2026-10-01');
    await page.locator('dialog').getByLabel('วันสิ้นสุดสัญญา').fill('2027-09-30');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByText('2026-10-01 → 2027-09-30').waitFor();
    await page.getByRole('button', {name: '+ เพิ่มช่วงสอบ', exact: true}).click();
    await page.locator('dialog').getByLabel('ชื่อช่วงสอบ').fill('สอบปลายภาค');
    await page.locator('dialog').getByLabel('หน่วยงาน', {exact: true}).selectOption({label: 'ภาควิชาอายุรศาสตร์'});
    await page.locator('dialog').getByLabel('เริ่ม (เวลาท้องถิ่นของอุปกรณ์)').fill('2026-10-05T09:00');
    await page.locator('dialog').getByLabel('สิ้นสุด (เวลาท้องถิ่นของอุปกรณ์)').fill('2026-10-05T12:00');
    await page.locator('dialog').getByRole('button', {name: 'บันทึก', exact: true}).click();
    await page.getByRole('cell', {name: 'สอบปลายภาค', exact: true}).waitFor();
    await page.evaluate(() => scrollTo(0, 0));
    await page.screenshot({path: path.join(output, 'registry-desktop.png'), fullPage: true});
    await page.getByRole('button', {name: 'เลือกบริบทลูกค้า', exact: true}).click();
    await page.evaluate(() => {
      document.addEventListener('customer-context-change', event => {
        document.body.dataset.qaContext = JSON.stringify(event.detail);
      });
    });
    const search = page.getByRole('combobox', {name: 'ค้นหาลูกค้า', exact: true});
    const started = Date.now(); await search.fill('สมชาย');
    await page.getByRole('option', {name: /TU · คณะแพทยศาสตร์/}).waitFor();
    console.log('Autocomplete visible after', Date.now() - started, 'ms (local QA)');
    await page.getByRole('option', {name: /TU · คณะแพทยศาสตร์/}).click();
    await page.getByRole('combobox', {name: 'ระบบที่ลูกค้าใช้งาน', exact: true}).waitFor();
    assert.notEqual(await page.getByRole('combobox', {name: 'ระบบที่ลูกค้าใช้งาน', exact: true}).inputValue(), '');
    await page.getByRole('combobox', {name: 'หน่วยงาน', exact: true}).selectOption({label: 'ภาควิชาอายุรศาสตร์'});
    await page.getByRole('combobox', {name: 'รายวิชา / การสอบ', exact: true}).selectOption({label: 'MED101 (รายวิชา)'});
    assert.match(await page.locator('.context-output').innerText(), /"course_or_exam_id": 1/);
    await search.fill('unknown-customer');
    assert.equal(await page.locator('.context-output').count(), 0);
    assert.deepEqual(JSON.parse(await page.locator('body').getAttribute('data-qa-context')), {
      organization_id: null, contact_id: null, product_instance_id: null,
      department_id: null, course_or_exam_id: null,
    });
    // Dismiss before debounce completes: late results must not reopen the list.
    await search.fill('TU');
    await search.press('Escape');
    await page.waitForTimeout(350);
    assert.equal(await page.locator('#customer-choices').isVisible(), false);
    assert.equal(await search.getAttribute('aria-expanded'), 'false');
    await page.setViewportSize({width: 390, height: 844});
    await page.getByRole('button', {name: 'Customers', exact: true}).click();
    await page.getByRole('button', {name: 'TU · คณะแพทยศาสตร์', exact: true}).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({path: path.join(output, 'registry-mobile.png'), fullPage: true});
    await page.getByRole('button', {name: 'ออกจากระบบ', exact: true}).click();
    await page.getByLabel('ชื่อผู้ใช้', {exact: true}).fill('qa-auditor');
    await page.getByLabel('รหัสผ่าน', {exact: true}).fill('test-only-password');
    await page.getByRole('button', {name: 'เข้าสู่ระบบ', exact: true}).click();
    await page.getByRole('button', {name: 'TU · คณะแพทยศาสตร์', exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: '+ เพิ่มองค์กร', exact: true}).count(), 0);
    // A slow customer detail response must not append content to a new view.
    await page.route('**/api/v1/customers/organizations/*/contract', async route => {
      const response = await route.fetch();
      await new Promise(resolve => setTimeout(resolve, 300));
      await route.fulfill({response});
    });
    const slowResponse = page.waitForResponse(response => response.url().endsWith('/contract'));
    await page.getByRole('button', {name: 'TU · คณะแพทยศาสตร์', exact: true}).click();
    await page.getByRole('button', {name: 'Product Registry', exact: true}).click();
    await slowResponse;
    await page.getByRole('heading', {name: 'ทะเบียนผลิตภัณฑ์', exact: true}).waitFor();
    assert.equal(await page.getByRole('heading', {name: 'สัญญาลูกค้า', exact: true}).count(), 0);
    await page.getByRole('button', {name: 'ExamPlus', exact: true}).click();
    await page.getByRole('heading', {name: 'หมวดหมู่: อาการ', exact: true}).waitFor();
    assert.equal(await page.getByRole('button', {name: '+ เพิ่มอาการ', exact: true}).count(), 0);
    assert.equal(await page.getByRole('button', {name: 'เลือกนโยบาย SLA', exact: true}).count(), 0);
    assert.deepEqual(errors, []);
    console.log('UI workflow passed: login, CRUD, team, contract, exam, autocomplete, mobile, Auditor');
  } catch (error) {
    await page.screenshot({path: path.join(output, 'registry-ui-error.png'), fullPage: true});
    console.log('Browser errors:', errors);
    console.log('Notice:', await page.locator('#notice').textContent());
    console.log('Dialog:', await page.locator('dialog').textContent());
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
