import { expect, test } from "@playwright/test";

test("REL case linking, customer history and audit search", async ({
  page,
  baseURL,
}) => {
  await page.goto("/login");
  await page.getByLabel("ชื่อผู้ใช้", { exact: true }).fill("qa-admin");
  await page.getByLabel("รหัสผ่าน", { exact: true }).fill("test-only-password");
  await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
  await expect(page.getByRole("heading", { name: "งานของฉัน" })).toBeVisible();

  async function post(path: string, data: unknown) {
    const response = await page.request.post(`/api/backend${path}`, {
      headers: { origin: baseURL! },
      data,
    });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  }
  const key = `rel-${Date.now()}`;
  const organization = await post("/customers/organizations", { name: key });
  const master = await post("/tickets", {
    organization_id: organization.id,
    subject: "Master incident QA",
    channel: "phone",
  });
  const child = await post("/tickets", {
    organization_id: organization.id,
    subject: "Child report QA",
    channel: "phone",
  });

  await page.goto(`/cases/${child.id}`);
  const panel = page.locator("section").filter({
    has: page.getByRole("heading", { name: "เคสที่เชื่อมโยง" }),
  });
  await panel.getByLabel("ประเภทความสัมพันธ์").selectOption("child-of");
  await panel.getByLabel("ID ของเคสปลายทาง").fill(String(master.id));
  await panel.getByLabel("เหตุผล").fill(key);
  await panel.getByRole("button", { name: "เชื่อมเคส" }).click();
  await expect(
    panel.getByRole("link", { name: `เคส #${master.id}` }),
  ).toBeVisible();

  await page.goto("/customers");
  await page.getByRole("link", { name: key, exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Master incident QA/ }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: /Child report QA/ }),
  ).toBeVisible();

  await page.goto("/administration/audit-log");
  await page.getByLabel("คำค้น").fill(key);
  await page.getByRole("button", { name: "ค้นหา", exact: true }).click();
  const entry = page
    .getByRole("row")
    .filter({ hasText: "relationship_created" });
  await expect(
    entry.getByRole("link", { name: child.ticket_no }),
  ).toBeVisible();
});
