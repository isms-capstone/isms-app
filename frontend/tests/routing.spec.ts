import { test, expect, type Page } from "@playwright/test";
async function login(page: Page, username: string, baseURL: string) {
  const response = await page.request.post("/api/session", {
    headers: { origin: baseURL },
    data: { username, password: "test-only-password" },
  });
  expect(response.ok()).toBeTruthy();
}
test("ESC handoff, return, self-assign, bulk handover and admin policy", async ({
  page,
  baseURL,
}) => {
  test.setTimeout(60000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page, "qa-agent", baseURL!);
  const rows = await (
    await page.request.get("/api/backend/tickets?limit=100")
  ).json();
  const original = rows.find(
    (r: { ticket_no: string }) => r.ticket_no === "ESC-QA-HANDOFF",
  );
  const pickup = rows.find(
    (r: { ticket_no: string }) => r.ticket_no === "ESC-QA-PICKUP",
  );
  expect(original).toBeTruthy();
  await page.goto(`/cases/${original.id}`);
  const panel = page.getByRole("region", {
    name: "การส่งต่อและ Routing",
    exact: true,
  });
  await expect(
    panel.getByRole("heading", { name: "การส่งต่อและ Routing", exact: true }),
  ).toBeVisible();
  await panel.getByRole("button", { name: "ส่งต่อ Tier", exact: true }).click();
  await expect(
    panel.getByRole("button", { name: "ยืนยันส่งงาน", exact: true }),
  ).toBeDisabled();
  await panel
    .getByRole("combobox", { name: "ผู้รับงาน *", exact: true })
    .selectOption({ label: "qa-specialist · Tier 1" });
  await panel
    .getByLabel("เหตุผลในการส่งงาน *", { exact: true })
    .fill("ต้องตรวจสอบบริการฝั่งระบบ");
  await panel
    .getByLabel("สิ่งที่ตรวจสอบไปแล้ว *", { exact: true })
    .fill("ตรวจสอบ log และลองทำซ้ำแล้ว");
  await panel
    .getByLabel("สิ่งที่ต้องการให้ช่วย *", { exact: true })
    .fill("ตรวจสอบสาเหตุและแนะนำวิธีแก้ไข");
  await panel
    .getByRole("button", { name: "ยืนยันส่งงาน", exact: true })
    .click();
  await expect(panel.locator(".routing-ownership")).toContainText(
    "qa-specialist",
  );
  await expect(panel.locator(".routing-timeline")).toContainText(
    "ตรวจสอบ log และลองทำซ้ำแล้ว",
  );
  await page.screenshot({
    path: "test-results/esc-case-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  let saved = await (
    await page.request.get(`/api/backend/tickets/${original.id}`)
  ).json();
  expect(saved.owner_id).toBe(original.owner_id);
  expect(saved.assignee_id).not.toBe(original.assignee_id);
  await login(page, "qa-specialist", baseURL!);
  await page.reload();
  await panel.getByRole("button", { name: "ส่งคืนเคส", exact: true }).click();
  await panel
    .getByLabel("เหตุผล / คำแนะนำในการส่งคืน *", { exact: true })
    .fill("ล้าง cache และตรวจสอบการเชื่อมต่ออีกครั้ง");
  await panel
    .getByRole("button", { name: "ยืนยันส่งงาน", exact: true })
    .click();
  await expect(panel.locator(".routing-ownership dd").nth(1)).toHaveText(
    "qa-agent",
  );
  saved = await (
    await page.request.get(`/api/backend/tickets/${original.id}`)
  ).json();
  expect(saved.ticket_no).toBe(original.ticket_no);
  expect(saved.assignee_id).toBe(original.assignee_id);
  expect(saved.created_at).toBe(original.created_at);
  await login(page, "qa-agent", baseURL!);
  await page.goto(`/cases/${pickup.id}`);
  await panel.getByRole("button", { name: "รับเคสนี้", exact: true }).click();
  await expect(
    panel.getByRole("button", { name: "รับเคสนี้", exact: true }),
  ).toHaveCount(0);
  await page.goto("/routing");
  await page
    .getByLabel("พร้อมรับงานใหม่และงานส่งต่อ", { exact: true })
    .uncheck();
  await expect(page.getByRole("status")).toContainText("ไม่พร้อมรับงาน");
  await page
    .getByRole("combobox", { name: "ผู้รับงานแทน *", exact: true })
    .selectOption({ label: "qa-peer · Tier 2" });
  await page
    .getByLabel("เหตุผลในการส่งมอบ *", { exact: true })
    .fill("ลาพักร้อน ส่งมอบงานให้ทีมดูแลต่อ");
  await page.screenshot({
    path: "test-results/esc-handover-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: /^ส่งมอบทั้งหมด/ }).click();
  await expect(page.getByRole("status")).toContainText("ส่งมอบงานแล้ว 3 เคส");
  await expect(
    page.getByText("ไม่มีเคสที่ต้องส่งมอบ", { exact: true }),
  ).toBeVisible();
  await login(page, "qa-admin", baseURL!);
  await page.goto("/routing/admin");
  await page.getByLabel("S1 timeout minutes", { exact: true }).fill("10");
  await page.getByRole("button", { name: "บันทึกนโยบาย", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("บันทึกการตั้งค่าแล้ว");
  expect(
    (await (await page.request.get("/api/backend/routing/config")).json())
      .policy.s1_minutes,
  ).toBe(10);
  await page.screenshot({
    path: "test-results/esc-admin-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByRole("button", { name: /^การแจ้งเตือน / }).click();
  await expect(
    page.getByRole("region", { name: "รายการแจ้งเตือน", exact: true }),
  ).toContainText("NEW ค้างเกิน 15 นาที");
  await page.keyboard.press("Escape");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/esc-admin-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.goto(`/cases/${original.id}`);
  await expect(panel).toBeVisible();
  await page.screenshot({
    path: "test-results/esc-case-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await login(page, "qa-auditor", baseURL!);
  await page.reload();
  await expect(panel).toBeVisible();
  await expect(panel.locator(".routing-actions .ui-button")).toHaveCount(0);
  const denial = await page.request.put("/api/backend/routing/policy", {
    headers: { origin: baseURL! },
    data: { s1_minutes: 1 },
  });
  expect(denial.status()).toBe(403);
  expect(errors).toEqual([]);
});

test("ESC BFF rejects cross-origin PUT before accessing configuration", async ({
  request,
}) => {
  const result = await request.put("/api/backend/routing/policy", {
    headers: { origin: "https://invalid.example" },
    data: { s1_minutes: 1 },
  });
  expect(result.status()).toBe(403);
});
