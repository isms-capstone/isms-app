import { test, expect } from "@playwright/test";

test("SIM and WRK persist through the current UI, API, CAT and unified timeline", async ({
  page,
  baseURL,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const headers = { origin: baseURL! };
  const login = await page.request.post("/api/session", {
    headers,
    data: { username: "qa-admin", password: "test-only-password" },
  });
  expect(login.ok()).toBe(true);
  async function post(path: string, data: unknown) {
    const response = await page.request.post(`/api/backend${path}`, {
      headers,
      data,
    });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  }
  const key = `sim-live-${Date.now()}`;
  const organization = await post("/customers/organizations", { name: key });
  const product = await post("/products", { code: key, name: key });
  const productModule = await post(`/products/${product.id}/modules`, {
    code: "login",
    name: "Login",
  });
  const category = await post("/admin/master-data/problem-types", {
    module_id: productModule.id,
    name: "Login failure",
  });
  const instance = await post(
    `/organizations/${organization.id}/products/${product.id}/instances`,
    {
      code: "production",
      name: "Exam instance",
      version: "1",
      environment: "production",
      url: "https://example.org",
    },
  );
  const query = `ระบบสอบไม่สามารถเข้าสู่ระบบได้ ${key}`;
  const source = await post("/tickets", {
    organization_id: organization.id,
    product_instance_id: instance.id,
    module_id: productModule.id,
    category_id: category.id,
    subject: query,
    channel: "phone",
    impact_scope: "organization",
    is_exam_window: false,
    severity: "S2",
    resolution_detail: "รีเซ็ตรหัสผ่านและเข้าสู่ระบบใหม่",
  });
  await page.goto("/cases/new");
  await page.getByRole("combobox").first().fill(key);
  await page.getByRole("option", { name: new RegExp(key) }).click();
  await page.getByRole("button", { name: "โทรศัพท์", exact: true }).click();
  await page.getByLabel("หัวข้อ *", { exact: true }).fill(query);
  const panel = page.getByRole("region", { name: "เคสที่คล้ายกัน" });
  await expect(
    panel.getByText(source.ticket_no, { exact: false }),
  ).toBeVisible();
  await panel.getByRole("radio", { name: "เลือกเคสนี้" }).check();
  await panel
    .getByRole("radio", { name: "ใช้วิธีแก้เดิม", exact: true })
    .check();
  await panel
    .getByRole("textbox", { name: "ขั้นตอนการแก้", exact: true })
    .fill("ขั้นตอนที่ผู้ใช้ตรวจและแก้ไขแล้ว");
  await panel.getByRole("button", { name: "ยืนยันการเลือก" }).click();
  await expect(
    page.getByRole("button", { name: "สร้างเคส", exact: true }),
  ).toBeEnabled();
  const imageBytes = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aR1sAAAAASUVORK5CYII=",
    "base64",
  );
  await page.locator('input[type="file"]').setInputFiles({
    name: "case-evidence.png",
    mimeType: "image/png",
    buffer: imageBytes,
  });
  await page.getByRole("button", { name: "สร้างเคส", exact: true }).click();
  await expect(page).toHaveURL(/\/cases\/\d+$/);
  const preview = page.getByRole("img", { name: "case-evidence.png" });
  await expect(preview).toBeVisible();
  await expect
    .poll(() => preview.evaluate((img: HTMLImageElement) => img.naturalWidth))
    .toBe(1);
  const download = await page.request.get((await preview.getAttribute("src"))!);
  expect(await download.body()).toEqual(imageBytes);
  const targetId = Number(new URL(page.url()).pathname.split("/").at(-1));
  const stored = await (
    await page.request.get(`/api/backend/tickets/${targetId}`)
  ).json();
  expect(stored).toMatchObject({
    severity: "S2",
    category_id: category.id,
    product_instance_id: instance.id,
    resolution_detail: "ขั้นตอนที่ผู้ใช้ตรวจและแก้ไขแล้ว",
  });
  const audit = await (
    await page.request.get(`/api/backend/tickets/${targetId}/audit`)
  ).json();
  expect(
    audit.some(
      (row: { event: string; changes: { decision?: string } }) =>
        row.event === "similarity_decision" && row.changes.decision === "reuse",
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "ค้นหาเคสคล้ายอีกครั้ง" }).click();
  await panel.getByRole("radio", { name: "เลือกเคสนี้" }).check();
  await panel
    .getByRole("radio", { name: "ผูกกับรายการเดิม", exact: true })
    .check();
  await panel.getByRole("button", { name: "ยืนยันการเลือก" }).click();
  await expect(page.locator(".timeline-event.similarity_decision")).toHaveCount(
    2,
  );
  await expect(page.locator(".timeline-event.case_created")).toHaveCount(1);
  await expect(page.locator(".timeline-event.status_changed")).toHaveCount(0);
  const links = await (
    await page.request.get(`/api/backend/tickets/${targetId}/links`)
  ).json();
  expect(links).toHaveLength(1);
  expect([links[0].ticket_id, links[0].related_ticket_id].sort()).toEqual(
    [source.id, targetId].sort(),
  );
  const composer = page.locator(".worklog-composer");
  await composer
    .getByLabel("ข้อความ *", { exact: true })
    .fill("SIM QA INTERNAL SECRET");
  await composer
    .getByRole("button", { name: "บันทึกข้อความ", exact: true })
    .click();
  await expect(page.locator(".timeline-event.internal_note")).toContainText(
    "SIM QA INTERNAL SECRET",
  );
  for (const channel of ["portal", "line", "email"]) {
    const response = await page.request.get(
      `/api/backend/tickets/${targetId}/external-replies/${channel}`,
    );
    expect(response.ok()).toBe(true);
    expect(await response.text()).not.toContain("INTERNAL SECRET");
  }
  const workAudit = await (
    await page.request.get(`/api/backend/tickets/${targetId}/audit`)
  ).json();
  expect(
    workAudit.some(
      (row: {
        event: string;
        actor_id: number;
        created_at: string;
        changes: { kind?: string };
      }) =>
        row.event === "worklog_created" &&
        row.actor_id &&
        row.created_at &&
        row.changes.kind === "internal_note",
    ),
  ).toBe(true);
  await page.screenshot({
    path: testInfo.outputPath("sim-wrk-integrated.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 375, height: 900 });
  await panel.scrollIntoViewIfNeeded();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("sim-mobile.png") });
  expect(errors).toEqual([]);
});
