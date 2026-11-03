import { test, expect, type Page } from "@playwright/test";

async function choose(page: Page, label: string, name: string) {
  // Exactly two activations: open the field, choose its value.
  await page.getByLabel(label, { exact: true }).click();
  await page.getByRole("group", { name: `ตัวเลือก${label}`, exact: true }).getByRole("button", { name, exact: true }).click();
}

test("WRK/CAT real persistence, mobile two-tap categories, audit and tag report", async ({ page, baseURL }) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/login");
  await page.getByLabel("ชื่อผู้ใช้", { exact: true }).fill("qa-admin");
  await page.getByLabel("รหัสผ่าน", { exact: true }).fill("test-only-password");
  await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
  await expect(page.getByRole("heading", { name: "งานของฉัน", exact: false })).toBeVisible();
  const headers = { origin: baseURL! };
  const key = `wrkcat-${Date.now()}`;
  async function post(path: string, data: unknown) {
    const response = await page.request.post(`/api/backend${path}`, { headers, data });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  }
  const org = await post("/customers/organizations", { name: key });
  const product = await post("/products", { code: key, name: key });
  const teacherModule = await post(`/products/${product.id}/modules`, { code: "teacher", name: "Teacher QA" });
  const module2 = await post(`/products/${product.id}/modules`, { code: "student", name: "Student QA" });
  const symptom = await post("/admin/master-data/symptoms", { product_id: product.id, name: "Download QA" });
  const stage = await post("/admin/master-data/service-stages", { product_id: product.id, name: "During exam QA" });
  const instance = await post(`/organizations/${org.id}/products/${product.id}/instances`, { code: "prod", name: "QA instance", version: "1", environment: "production", url: "https://example.org" });
  const ticket = await post("/tickets", { organization_id: org.id, product_instance_id: instance.id, subject: key, channel: "phone" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/cases/${ticket.id}`);
  await expect(page.getByRole("heading", { name: "หมวดหมู่และการประเมินเคส" })).toBeVisible();
  await expect(page.getByLabel("โมดูล (Module)", { exact: true })).not.toHaveAttribute("aria-disabled", "true");
  await choose(page, "โมดูล (Module)", "Teacher QA");
  await choose(page, "อาการ", "Download QA");
  await choose(page, "ช่วงเวลาของการสอบ", "During exam QA");
  await choose(page, "ขอบเขตผลกระทบ", "ทั้งองค์กร / ทั้งห้องสอบ");
  await page.getByLabel("ช่วงเวลาที่เกิดเหตุ", { exact: true }).selectOption("true");
  await expect(page.getByLabel("Severity", { exact: true }).locator("option").first()).toContainText("S1");
  await page.getByLabel("แท็กอิสระ", { exact: true }).fill(key);
  await page.getByRole("button", { name: "เพิ่มแท็ก", exact: true }).click();
  await page.getByRole("button", { name: "บันทึกหมวดหมู่", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "บันทึกหมวดหมู่" })).toBeVisible();
  await choose(page, "โมดูล (Module)", "Student QA");
  await page.getByRole("button", { name: "บันทึกหมวดหมู่", exact: true }).click();
  const fields = await (await page.request.get(`/api/backend/tickets/${ticket.id}/categorization`)).json();
  expect(fields.module_id).toBe(module2.id);
  expect(fields.symptom_id).toBe(symptom.id);
  expect(fields.service_stage_id).toBe(stage.id);
  expect(fields.severity).toBe("S1");
  const composer = page.locator(".worklog-composer").last();
  await composer.getByLabel("ข้อความ *", { exact: true }).fill("ข้อมูลภายใน QA");
  await composer.getByRole("button", { name: "บันทึกข้อความ", exact: true }).click();
  await expect(page.locator(".timeline-event.internal_note")).toContainText("ข้อมูลภายใน QA");
  await composer.getByRole("button", { name: "Public Reply", exact: true }).click();
  await composer.getByLabel("ช่องทางที่ส่งจริง *", { exact: true }).selectOption("line_oa");
  await composer.getByLabel("ข้อความ *", { exact: true }).fill("แจ้งลูกค้าทาง LINE แล้ว QA");
  await composer.getByRole("button", { name: "บันทึกข้อความ", exact: true }).click();
  await expect(page.locator(".timeline-event.public_reply")).toContainText("LINE OA");
  await page.reload();
  await expect(page.locator(".timeline-event.public_reply")).toContainText("แจ้งลูกค้าทาง LINE แล้ว QA");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: "test-results/wrk-cat-mobile.png", fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1050 });
  await page.screenshot({ path: "test-results/wrk-cat-desktop.png", fullPage: true });
  await page.goto("/reports/popular-tags");
  await expect(page.getByRole("row").filter({ hasText: key })).toContainText("1");
  expect(errors).toEqual([]);
  // Existing CAP ownership, CORE status and intake channel are preserved.
  const saved = await (await page.request.get(`/api/backend/tickets/${ticket.id}`)).json();
  expect(saved.channel).toBe("phone");
  expect(saved.status).toBe("NEW");
  expect(saved.owner_id).toBe(ticket.owner_id);
  expect(teacherModule.id).not.toBe(module2.id);
});
