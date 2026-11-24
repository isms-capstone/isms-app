import { expect, test } from "@playwright/test";

test("SEA searches Thai worklogs and exports a saved view, then AUD records cancellation", async ({
  page,
  baseURL,
}) => {
  const headers = { origin: baseURL! };
  const login = await page.request.post("/api/session", {
    headers,
    data: { username: "qa-admin", password: "test-only-password" },
  });
  expect(login.ok()).toBe(true);
  const marker = `sea-browser-${Date.now()}`;
  const organization = await page.request.post(
    "/api/backend/customers/organizations",
    {
      headers,
      data: { name: marker },
    },
  );
  expect(organization.ok()).toBe(true);
  const ticket = await page.request.post("/api/backend/tickets", {
    headers,
    data: {
      organization_id: (await organization.json()).id,
      subject: marker,
      channel: "phone",
      impact_scope: "organization",
      is_exam_window: true,
    },
  });
  expect(ticket.ok(), await ticket.text()).toBe(true);
  const id = (await ticket.json()).id;
  const worklog = await page.request.post(
    `/api/backend/tickets/${id}/worklogs`,
    {
      headers,
      data: { kind: "internal_note", body: "ตรวจพบว่าเข้าสู่ระบบไม่ได้" },
    },
  );
  expect(worklog.ok(), await worklog.text()).toBe(true);

  await page.goto("/cases");
  await page.getByRole("link", { name: "ค้นหาเคส", exact: true }).click();
  await page
    .getByRole("textbox", { name: "คำค้น", exact: true })
    .fill("เข้าสู่ระบบไม่ได้");
  await page
    .getByRole("combobox", { name: "ลูกค้า", exact: true })
    .selectOption({ label: marker });
  await page.getByRole("combobox", { name: "Severity", exact: true }).selectOption("S1");
  await page.getByRole("button", { name: "ค้นหา", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "ผลการค้นหา 1 เคส" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: new RegExp(marker) }),
  ).toHaveAttribute("href", `/cases/${id}`);

  await page
    .getByRole("textbox", { name: "ชื่อมุมมอง", exact: true })
    .fill(marker);
  await page.getByRole("button", { name: "บันทึกมุมมอง", exact: true }).click();
  const view = page.getByRole("button", { name: `${marker} · ส่วนตัว` });
  await expect(view).toBeVisible();
  await page.reload();
  await view.click();
  await expect(
    page.getByRole("heading", { name: "ผลการค้นหา 1 เคส" }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "ส่งออก Excel", exact: true }).click();
  expect((await download).suggestedFilename()).toBe("cases.xlsx");

  await page.getByRole("link", { name: new RegExp(marker) }).click();
  await page.getByRole("button", { name: "ยกเลิกเคส (สร้างผิด)", exact: true }).click();
  const reason = page.getByRole("textbox", { name: "เหตุผลเปลี่ยนสถานะ" });
  await expect(reason).toHaveAttribute("required", "");
  await reason.fill("เคสทดสอบสำหรับตรวจประวัติการยกเลิก");
  await page.getByRole("button", { name: "ยืนยันเปลี่ยนสถานะ" }).click();
  const audit = page.locator(".timeline-event.ticket_fields_updated").filter({
    hasText: "เปลี่ยนข้อมูลสำคัญของเคส",
  });
  await audit.getByText("ค่าเดิม / ค่าใหม่", { exact: true }).click();
  await expect(audit).toContainText("NEW");
  await expect(audit).toContainText("CANCELLED");
  await page.reload();
  await expect(page.locator(".timeline-event.ticket_fields_updated")).toBeVisible();
});
