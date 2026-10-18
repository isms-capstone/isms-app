import { test, expect } from "@playwright/test";
test("preview: SLA ordering, filters, keyboard drawer, navigation and responsive layouts", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/preview/my-work");
  await expect(
    page.getByRole("heading", { name: "คิวเคสที่เปิดอยู่", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".case-table tbody tr")).toHaveCount(6);
  await expect(page.locator(".gd-Table__cell").first()).toBeVisible();
  await expect(page.locator(".gd-Tag__tag").first()).toBeVisible();
  await expect(page.locator(".gd-Button__button").first()).toBeVisible();
  const palette = await page.evaluate(() => {
    const css = getComputedStyle(document.documentElement);
    return [
      "--label-primary",
      "--fill-element-brand",
      "--label-muted",
      "--fill-element-success",
      "--fill-element-danger",
      "--background-primary",
    ].map((name) => css.getPropertyValue(name).trim());
  });
  expect(palette).toEqual([
    "#060b0f",
    "#33454e",
    "#76949f",
    "#73e8af",
    "#9e2a2b",
    "#fbf5f3",
  ]);
  const firstCheckbox = page.getByRole("checkbox", {
    name: "เลือกเคส DVHT-202609-00418",
    exact: true,
  });
  await firstCheckbox.check();
  await expect(firstCheckbox).toBeChecked();
  await expect(page).toHaveURL(/\/preview\/my-work$/);
  await page
    .getByRole("checkbox", { name: "เลือกเคสในหน้านี้ทั้งหมด", exact: true })
    .check();
  await expect(page.locator(".case-table tbody input:checked")).toHaveCount(6);
  await page
    .getByRole("checkbox", { name: "เลือกเคสในหน้านี้ทั้งหมด", exact: true })
    .uncheck();
  await expect(page.locator(".case-table tbody tr").first()).toContainText(
    "00418",
  );
  await page.screenshot({
    path: "test-results/my-work-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.getByLabel("กรองผลิตภัณฑ์", { exact: true }).selectOption("GetA");
  await expect(page.locator(".case-table tbody tr")).toHaveCount(2);
  await page.getByLabel("กรองผลิตภัณฑ์", { exact: true }).selectOption("");
  await page
    .getByRole("button", { name: "ตัวกรองเพิ่มเติม", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("dialog").getByLabel("S1", { exact: true }).check();
  await page.getByRole("button", { name: "ใช้ตัวกรอง", exact: true }).click();
  await expect(page.locator(".case-table tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "ล้างทั้งหมด", exact: true }).click();
  await expect(page.locator(".case-table tbody tr")).toHaveCount(6);
  await page.getByRole("link", { name: "All Cases", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "เคสทั้งหมด", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "ตัวกรอง", exact: true }).click();
  await page.screenshot({
    path: "test-results/all-cases-drawer-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByLabel("ค้นหาเคส", { exact: true }).fill("Blueprint");
  await expect(page.locator(".case-table tbody tr")).toHaveCount(1);
  await page.getByRole("link", { name: "สร้างเคส", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "ข้อมูลเริ่มต้น", exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/create-case-desktop.png",
    fullPage: true,
    animations: "disabled",
  });
  let writes = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && r.url().endsWith("/api/backend/tickets"))
      writes++;
  });
  await page.getByRole("button", { name: "สร้างเคส", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Design Preview");
  expect(writes).toBe(0);
  for (const width of [768, 375]) {
    await page.setViewportSize({ width, height: 812 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/create-case-${width}.png`,
      fullPage: true,
      animations: "disabled",
    });
  }
  await page
    .getByRole("button", { name: "เปิดหรือปิดเมนู", exact: true })
    .click();
  await page.getByRole("link", { name: /^My Work/ }).click();
  await expect(page.locator(".case-table tbody tr")).toHaveCount(6);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/my-work-mobile.png",
    fullPage: true,
    animations: "disabled",
  });
  expect(errors).toEqual([]);
});
test("live: HttpOnly login, real case creation, manual draft edit and logout", async ({
  page,
  baseURL,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/login");
  await page.getByLabel("ชื่อผู้ใช้", { exact: true }).fill("qa-admin");
  await page.getByLabel("รหัสผ่าน", { exact: true }).fill("test-only-password");
  await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "งานของฉัน", exact: false }),
  ).toBeVisible();
  await expect(page.locator(".data-note")).toContainText("ยังไม่มีข้อมูล SLA");
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    "isms_access",
  );
  const cookies = await page.context().cookies();
  expect(
    cookies.find((cookie) => cookie.name === "isms_access")?.httpOnly,
  ).toBe(true);
  const headers = { origin: baseURL! };
  const orgName = `Frontend QA ${Date.now()} · คณะแพทยศาสตร์`;
  const organization = await page.request.post(
    "/api/backend/customers/organizations",
    { headers, data: { name: orgName, is_active: true } },
  );
  expect(organization.ok()).toBe(true);
  const org = await organization.json();
  await page.getByRole("link", { name: "สร้างเคส", exact: true }).click();
  await page
    .getByRole("combobox", { name: "ลูกค้า / ผู้แจ้ง *" })
    .fill(orgName);
  await page.getByRole("option", { name: new RegExp(orgName) }).click();
  await page
    .getByLabel("หัวข้อ *", { exact: true })
    .fill("ตรวจการสร้างเคส Next.js");
  await page.getByRole("button", { name: "โทรศัพท์", exact: true }).click();
  await page.getByRole("button", { name: "สร้างเคส", exact: true }).click();
  await expect(page.getByRole("heading", { name: /^DVHT-/ })).toBeVisible();
  const id = page.url().split("/").at(-1);
  const saved = await (
    await page.request.get(`/api/backend/tickets/${id}`)
  ).json();
  expect(saved.organization_id).toBe(org.id);
  expect(saved.status).toBe("NEW");
  expect(saved.channel).toBe("phone");
  const draftName = `Draft frontend QA ${Date.now()}`;
  const editedName = `${draftName} updated`;
  const draftResponse = await page.request.post("/api/backend/tickets", {
    headers,
    data: { subject: draftName, save_as_draft: true },
  });
  expect(draftResponse.ok()).toBe(true);
  const draft = await draftResponse.json();
  await page.goto("/my-work");
  await expect(page.getByText(draftName, { exact: true })).toBeVisible();
  const draftItem = page.locator(".draft-item").filter({ hasText: draftName });
  await draftItem
    .getByRole("button", { name: "เติมข้อมูลต่อ", exact: true })
    .click();
  await draftItem.getByLabel("หัวข้อเคส", { exact: true }).fill(editedName);
  await draftItem
    .getByRole("button", { name: "บันทึกช่องนี้", exact: true })
    .click();
  await expect(page.getByText(editedName, { exact: true })).toBeVisible();
  const updated = await (
    await page.request.get(`/api/backend/tickets/${draft.id}`)
  ).json();
  expect(updated.status).toBe("DRAFT");
  expect(updated.ticket_no).toBe(null);
  await page.getByRole("button", { name: "ออกจากระบบ", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "เข้าสู่ระบบ ISMS", exact: true }),
  ).toBeVisible();
  expect(
    (await page.request.get("/api/backend/registry/session")).status(),
  ).toBe(401);
  expect(errors).toEqual([]);
});
test("BFF rejects cross-origin writes and preserves authorization", async ({
  request,
}) => {
  expect(
    (
      await request.post("/api/session", {
        headers: { origin: "https://invalid.example" },
        data: { username: "qa-admin", password: "test-only-password" },
      })
    ).status(),
  ).toBe(403);
  expect((await request.get("/api/backend/registry/session")).status()).toBe(
    401,
  );
});

test("read-only role: API denial, inline error recovery and empty search", async ({
  page,
  baseURL,
}) => {
  await page.route("**/api/backend/tickets?*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Temporary QA failure" }),
    }),
  );
  await page.goto("/login");
  await page.getByLabel("ชื่อผู้ใช้", { exact: true }).fill("qa-auditor");
  await page.getByLabel("รหัสผ่าน", { exact: true }).fill("test-only-password");
  await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: "Temporary QA failure" }),
  ).toBeVisible();
  await page.unroute("**/api/backend/tickets?*");
  await page.getByRole("button", { name: "ลองอีกครั้ง", exact: true }).click();
  await expect(page.locator(".data-note")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "สร้างเคส", exact: true }),
  ).toHaveCount(0);
  const response = await page.request.post("/api/backend/tickets", {
    headers: { origin: baseURL! },
    data: { subject: "must not persist", save_as_draft: true },
  });
  expect(response.status()).toBe(403);
  await page
    .getByLabel("ค้นหาเคส", { exact: true })
    .fill("no-such-case-qa-729148");
  await expect(
    page.getByRole("heading", {
      name: "ไม่มีเคสที่ต้องดำเนินการ",
      exact: true,
    }),
  ).toBeVisible();
});
