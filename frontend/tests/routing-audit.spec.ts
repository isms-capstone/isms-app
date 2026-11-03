import { chooseOption } from "./company-controls";
import { test, expect, type Page } from "@playwright/test";
test.use({ video: "on", trace: "on" });
async function loginUI(page: Page, name: string) {
  await page.goto("/login");
  await page.getByLabel("ชื่อผู้ใช้", { exact: true }).fill(name);
  await page.getByLabel("รหัสผ่าน", { exact: true }).fill("test-only-password");
  await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
  await expect(page).toHaveURL(/\/my-work$/);
  await expect(
    page.getByRole("heading", { name: "งานของฉัน", exact: false }),
  ).toBeVisible();
}
async function cases(page: Page) {
  return (await page.request.get("/api/backend/tickets?limit=100")).json();
}
async function caseBy(page: Page, no: string) {
  return (await cases(page)).find(
    (t: { ticket_no: string }) => t.ticket_no === no,
  );
}
async function routing(page: Page, id: number) {
  return (await page.request.get(`/api/backend/tickets/${id}/routing`)).json();
}
function panel(page: Page) {
  return page.getByRole("region", {
    name: "การส่งต่อและ Routing",
    exact: true,
  });
}
async function shot(page: Page, name: string) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: `test-results/${name}.png`,
    fullPage: true,
    animations: "disabled",
  });
}

test("ESC-01 all Admin forms persist and editing a user preserves their current tier", async ({
  page,
}) => {
  test.setTimeout(90000);
  await loginUI(page, "qa-admin");
  await page.goto("/routing/admin");
  const cards = page.locator(".routing-admin-grid > section");
  await expect(
    page.getByRole("region", { name: "เริ่มตั้งค่าการส่งต่อ" }),
  ).toBeVisible();
  const routes = cards.nth(0);
  for (const [tier, team] of [
    [2, "Support"],
    [1, "QA Specialists"],
    [0, "QA Developers"],
  ] as const) {
    await chooseOption(
      page,
      routes.getByRole("combobox", { name: "ผลิตภัณฑ์", exact: true }),
      { label: "ESC QA Product" },
    );
    await chooseOption(
      page,
      routes.getByRole("combobox", { name: "Tier", exact: true }),
      String(tier),
    );
    await chooseOption(
      page,
      routes.getByRole("combobox", { name: "ทีมปลายทาง", exact: true }),
      { label: team },
    );
    await routes.getByRole("button", { name: "บันทึกเส้นทาง" }).click();
    await expect(page.getByRole("status")).toContainText(
      "บันทึกการตั้งค่าแล้ว",
    );
    await expect(
      routes.getByRole("button", { name: "บันทึกเส้นทาง" }),
    ).toBeEnabled();
  }
  const leader = cards.nth(1);
  await chooseOption(
    page,
    leader.getByRole("combobox", { name: "ทีม", exact: true }),
    { label: "Support" },
  );
  await chooseOption(
    page,
    leader.getByRole("combobox", { name: "หัวหน้าทีม", exact: true }),
    { label: "qa-admin" },
  );
  await leader
    .getByRole("combobox", { name: "หัวหน้าทีม", exact: true })
    .click();
  await expect(
    page.getByRole("option", { name: "qa-developer", exact: true }),
  ).toHaveCount(0);
  await page.keyboard.press("Escape");
  await leader.getByRole("button", { name: "บันทึกหัวหน้าทีม" }).click();
  await expect(page.getByRole("status")).toContainText("บันทึกการตั้งค่าแล้ว");
  const user = cards.nth(2);
  await chooseOption(
    page,
    user.getByRole("combobox", { name: "ผู้ใช้", exact: true }),
    { label: "qa-specialist · Specialist" },
  );
  await expect(
    user.getByRole("combobox", { name: "Tier", exact: true }),
  ).toHaveText("Tier 1");
  await chooseOption(
    page,
    user.getByRole("combobox", { name: "Tier", exact: true }),
    "0",
  );
  await user.getByRole("button", { name: "บันทึก Tier" }).click();
  await expect
    .poll(
      async () =>
        (
          await (await page.request.get("/api/backend/routing/options")).json()
        ).users.find((u: { name: string }) => u.name === "qa-specialist")
          .default_tier,
    )
    .toBe(0);
  await chooseOption(
    page,
    user.getByRole("combobox", { name: "Tier", exact: true }),
    "1",
  );
  await user.getByRole("button", { name: "บันทึก Tier" }).click();
  await expect
    .poll(
      async () =>
        (
          await (await page.request.get("/api/backend/routing/options")).json()
        ).users.find((u: { name: string }) => u.name === "qa-specialist")
          .default_tier,
    )
    .toBe(1);
  const policy = cards.nth(3);
  if (await policy.getByRole("checkbox").isChecked())
    await policy.getByRole("checkbox").uncheck();
  await policy.getByLabel("S1 timeout minutes").fill("1");
  await chooseOption(page, policy.getByRole("combobox"), {
    label: "ESC QA all-day",
  });
  await policy.getByRole("button", { name: "บันทึกนโยบาย" }).click();
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/backend/routing/config")).json())
          .policy.s1_minutes,
    )
    .toBe(1);
  await page.reload();
  await expect(
    user.getByRole("combobox", { name: "ผู้ใช้", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".routing-config-list")).toContainText(
    "QA Developers",
  );
  await shot(page, "esc-audit-admin");
});

test("ESC-02..05 real browser sends Tier 2 to 1 to 0 and returns all the way before resolving the same case", async ({
  page,
}) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await loginUI(page, "qa-auto");
  const original = await caseBy(page, "ESC-AUDIT-CHAIN"),
    count = (await cases(page)).length;
  await page.goto(`/cases/${original.id}`);
  async function handoff(tier: number, label: string) {
    await panel(page)
      .getByRole("button", { name: "ส่งต่อ Tier", exact: true })
      .click();
    await chooseOption(
      page,
      panel(page).getByRole("combobox", { name: "Tier ปลายทาง", exact: true }),
      String(tier),
    );
    await chooseOption(
      page,
      panel(page).getByRole("combobox", { name: "ผู้รับงาน *", exact: true }),
      { label },
    );
    await panel(page)
      .getByLabel("เหตุผลในการส่งงาน *", { exact: true })
      .fill("   ");
    await expect(
      panel(page).getByRole("button", { name: "ยืนยันส่งงาน", exact: true }),
    ).toBeDisabled();
    await panel(page)
      .getByLabel("เหตุผลในการส่งงาน *", { exact: true })
      .fill("ต้องการตรวจปัญหาเชิงลึก");
    await panel(page)
      .getByLabel("สิ่งที่ตรวจสอบไปแล้ว *", { exact: true })
      .fill("ตรวจข้อมูลและทำซ้ำแล้ว");
    await expect(
      panel(page).getByRole("button", { name: "ยืนยันส่งงาน", exact: true }),
    ).toBeDisabled();
    await panel(page)
      .getByLabel("สิ่งที่ต้องการให้ช่วย *", { exact: true })
      .fill("ตรวจสาเหตุและให้คำแนะนำ");
    await panel(page)
      .getByRole("button", { name: "ยืนยันส่งงาน", exact: true })
      .click();
    await expect
      .poll(async () => (await routing(page, original.id)).tier)
      .toBe(tier);
    await expect(panel(page).locator(".routing-timeline")).toContainText(
      "ตรวจข้อมูลและทำซ้ำแล้ว",
    );
  }
  await handoff(1, "qa-specialist · Tier 1");
  await loginUI(page, "qa-specialist");
  await page.goto(`/cases/${original.id}`);
  await handoff(0, "qa-developer · Tier 0");
  await loginUI(page, "qa-developer");
  await page.goto(`/cases/${original.id}`);
  await expect
    .poll(async () => (await routing(page, original.id)).seconds_by_tier["0"], {
      timeout: 10000,
    })
    .toBeGreaterThan(0);
  await shot(page, "esc-audit-developer");
  async function sendBack(tier: number) {
    await panel(page)
      .getByRole("button", { name: "ส่งคืนเคส", exact: true })
      .click();
    await expect(
      panel(page).getByRole("button", { name: "ยืนยันส่งงาน", exact: true }),
    ).toBeDisabled();
    await panel(page)
      .getByLabel("เหตุผล / คำแนะนำในการส่งคืน *", { exact: true })
      .fill("ตรวจแล้ว ส่งกลับให้ทดสอบและประสานลูกค้า");
    await panel(page)
      .getByRole("button", { name: "ยืนยันส่งงาน", exact: true })
      .click();
    await expect
      .poll(async () => (await routing(page, original.id)).tier)
      .toBe(tier);
  }
  await sendBack(1);
  await loginUI(page, "qa-specialist");
  await page.goto(`/cases/${original.id}`);
  await sendBack(2);
  await loginUI(page, "qa-auto");
  await page.goto(`/cases/${original.id}`);
  let saved = await caseBy(page, "ESC-AUDIT-CHAIN");
  expect(saved.owner_id).toBe(original.owner_id);
  expect(saved.assignee_id).toBe(original.assignee_id);
  expect(saved.created_at).toBe(original.created_at);
  expect((await cases(page)).length).toBe(count);
  const state = await routing(page, original.id);
  expect(
    state.events.filter((e: { kind: string }) => e.kind === "return"),
  ).toHaveLength(2);
  expect(state.intervals).toHaveLength(5);
  expect(
    state.intervals.filter((i: { exited_at: string | null }) => !i.exited_at),
  ).toHaveLength(1);
  await page
    .locator(".lifecycle-panel")
    .getByRole("button", { name: "In Progress", exact: true })
    .click();
  await page
    .locator(".lifecycle-panel")
    .getByRole("button", { name: "ยืนยันเปลี่ยนสถานะ", exact: true })
    .click();
  await expect
    .poll(async () => (await caseBy(page, "ESC-AUDIT-CHAIN")).status)
    .toBe("IN_PROGRESS");
  await page
    .locator(".lifecycle-panel")
    .getByRole("button", { name: "Resolved", exact: true })
    .click();
  for (const [label, value] of [
    ["ประเภทปัญหา", "QA ESC issue"],
    ["สาเหตุปัญหา", "QA cause"],
    ["วิธีแก้ไข", "QA solution"],
  ])
    await chooseOption(
      page,
      page
        .locator(".lifecycle-panel")
        .getByRole("combobox", { name: label, exact: true }),
      { label: value },
    );
  await page
    .getByLabel("รายละเอียดการแก้ไข", { exact: true })
    .fill("ทดสอบสำเร็จและยืนยันกับลูกค้าแล้ว");
  await page
    .locator(".lifecycle-panel")
    .getByRole("button", { name: "ยืนยันเปลี่ยนสถานะ", exact: true })
    .click();
  await expect
    .poll(async () => (await caseBy(page, "ESC-AUDIT-CHAIN")).status)
    .toBe("RESOLVED");
  saved = await routing(page, original.id);
  expect(
    saved.intervals.every((i: { exited_at: string | null }) => i.exited_at),
  ).toBeTruthy();
  await shot(page, "esc-audit-return-and-resolve");
  expect(errors).toEqual([]);
});

test("ESC-07 Admin assigns through form and a read-only user cannot route", async ({
  page,
}) => {
  await loginUI(page, "qa-admin");
  const ticket = await caseBy(page, "ESC-AUDIT-ASSIGN");
  await page.goto(`/cases/${ticket.id}`);
  await panel(page)
    .getByRole("button", { name: "มอบหมายผู้รับผิดชอบ", exact: true })
    .click();
  await chooseOption(
    page,
    panel(page).getByRole("combobox", { name: "ผู้รับงาน *", exact: true }),
    { label: "qa-auto · Tier 2" },
  );
  await panel(page)
    .getByLabel("เหตุผลในการส่งงาน *", { exact: true })
    .fill("หัวหน้าแบ่งงานให้ผู้พร้อมรับ");
  await panel(page)
    .getByRole("button", { name: "ยืนยันส่งงาน", exact: true })
    .click();
  await expect
    .poll(async () => (await routing(page, ticket.id)).assignee?.name)
    .toBe("qa-auto");
  await loginUI(page, "qa-auditor");
  await page.goto(`/cases/${ticket.id}`);
  await expect(panel(page)).toBeVisible();
  await expect(panel(page).locator(".routing-actions button")).toHaveCount(0);
});

test("ESC-06/08 production worker performs the real five-minute scheduled check and updates the browser", async ({
  page,
}) => {
  test.skip(
    process.env.ESC_SCHEDULER_AUDIT !== "1",
    "Run with the isolated MariaDB API and production routing_worker process",
  );
  test.setTimeout(380000);
  await loginUI(page, "qa-admin");
  const s1 = await caseBy(page, "ESC-AUDIT-S1"),
    ack = await caseBy(page, "ESC-AUDIT-ACK"),
    stalled = await caseBy(page, "ESC-AUDIT-STALLED");
  await page.goto(`/cases/${ack.id}`);
  await panel(page)
    .getByRole("button", { name: "รับทราบและเริ่มตรวจสอบ", exact: true })
    .click();
  await expect
    .poll(async () => (await routing(page, ack.id)).first_response_at)
    .toBeTruthy();
  await page.goto("/routing/admin");
  const policy = page.locator(".routing-admin-grid > section").nth(3);
  await policy.getByRole("checkbox").check();
  await policy.getByLabel("S1 timeout minutes").fill("1");
  await chooseOption(page, policy.getByRole("combobox"), {
    label: "ESC QA all-day",
  });
  await policy.getByRole("button", { name: "บันทึกนโยบาย" }).click();
  await expect
    .poll(
      async () =>
        (await (await page.request.get("/api/backend/routing/config")).json())
          .policy.enabled,
    )
    .toBe(true);
  const firstState = await routing(page, s1.id);
  expect(firstState.tier).toBe(2);
  console.log(
    "Waiting for the actual worker cadence, with no clock mocking or direct routing mutations",
  );
  await expect
    .poll(async () => (await routing(page, s1.id)).tier, {
      timeout: 340000,
      intervals: [5000],
    })
    .toBe(1);
  const changed = await routing(page, s1.id);
  expect(changed.owner.id).toBe(s1.owner_id);
  expect(
    changed.events.some((e: { kind: string }) => e.kind === "auto_escalate"),
  ).toBeTruthy();
  expect((await routing(page, ack.id)).tier).toBe(2);
  await page.reload();
  await page.getByRole("button", { name: /^การแจ้งเตือน / }).click();
  await expect(
    page.getByRole("region", { name: "รายการแจ้งเตือน", exact: true }),
  ).toContainText("S1 ไม่มีการตอบสนอง");
  await expect(
    page.getByRole("region", { name: "รายการแจ้งเตือน", exact: true }),
  ).toContainText(stalled.ticket_no);
  await page.keyboard.press("Escape");
  await page.goto(`/cases/${s1.id}`);
  await expect(panel(page).locator(".routing-timeline")).toContainText(
    "ส่งต่ออัตโนมัติ",
  );
  await shot(page, "esc-audit-real-scheduler");
  const notices = await (
    await page.request.get("/api/backend/routing/notifications")
  ).json();
  expect(
    notices.some(
      (n: { ticket_id: number; kind: string }) =>
        n.ticket_id === stalled.id && n.kind === "new_stalled",
    ),
  ).toBeTruthy();
});
