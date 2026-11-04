import { test, expect, type Page } from "@playwright/test";
import { chooseOption } from "./company-controls";

test.beforeEach(() =>
  test.skip(
    process.env.CAT_QA_MARIADB !== "1",
    "Requires the disposable migrated MariaDB QA database",
  ),
);

async function login(page: Page, baseURL: string, username = "qa-admin") {
  const result = await page.request.post("/api/session", {
    headers: { origin: baseURL },
    data: { username, password: "test-only-password" },
  });
  expect(result.ok(), await result.text()).toBe(true);
}

async function choose(page: Page, label: string, name: string) {
  const control = page.getByLabel(label, { exact: true });
  await expect(control).not.toHaveAttribute("aria-disabled", "true");
  await control.tap();
  const menu = page.getByRole("group", {
    name: `ตัวเลือก${label}`,
    exact: true,
  });
  await expect(menu).toBeVisible();
  await menu.getByRole("button", { name, exact: true }).tap();
  await expect(menu).toBeHidden();
}

async function saveCategories(page: Page) {
  const button = page.getByRole("button", {
    name: "บันทึกหมวดหมู่",
    exact: true,
  });
  const response = page.waitForResponse(
    (r) =>
      r.request().method() === "PATCH" && r.url().endsWith("/categorization"),
  );
  await expect(button).toBeEnabled();
  await button.click();
  const saved = await response;
  expect(saved.status(), await saved.text()).toBe(200);
  await expect(button).toBeEnabled();
}

async function setup(page: Page, baseURL: string) {
  await login(page, baseURL);
  const headers = { origin: baseURL };
  const key = `cat-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
  async function post(path: string, data: unknown) {
    const response = await page.request.post(`/api/backend${path}`, {
      headers,
      data,
    });
    expect(response.ok(), await response.text()).toBe(true);
    return response.json();
  }
  const org = await post("/customers/organizations", { name: key });
  const productA = await post("/products", {
    code: `${key}-a`,
    name: `${key} A`,
  });
  const productB = await post("/products", {
    code: `${key}-b`,
    name: `${key} B`,
  });
  const teacher = await post(`/products/${productA.id}/modules`, {
    code: "teacher",
    name: "Teacher",
  });
  const student = await post(`/products/${productA.id}/modules`, {
    code: "student",
    name: "Student",
  });
  const clinic = await post(`/products/${productB.id}/modules`, {
    code: "clinic",
    name: "Clinic",
  });
  const symptomA = await post("/admin/master-data/symptoms", {
    product_id: productA.id,
    name: "Download failure",
  });
  const symptomB = await post("/admin/master-data/symptoms", {
    product_id: productB.id,
    name: "Mapping error",
  });
  const stageA = await post("/admin/master-data/service-stages", {
    product_id: productA.id,
    name: "During exam",
  });
  const stageB = await post("/admin/master-data/service-stages", {
    product_id: productB.id,
    name: "General",
  });
  const problemA = await post("/admin/master-data/problem-types", {
    module_id: teacher.id,
    name: "Teacher access",
  });
  const problemB = await post("/admin/master-data/problem-types", {
    module_id: clinic.id,
    name: "Clinic access",
  });
  const instanceA = await post(
    `/organizations/${org.id}/products/${productA.id}/instances`,
    {
      code: "a",
      name: "Instance A",
      version: "1",
      environment: "production",
      url: "https://example.org",
    },
  );
  const instanceB = await post(
    `/organizations/${org.id}/products/${productB.id}/instances`,
    {
      code: "b",
      name: "Instance B",
      version: "1",
      environment: "production",
      url: "https://example.org",
    },
  );
  const cause = await post("/admin/master-data/cause-codes", {
    code: key,
    name: "Configuration QA",
  });
  const solution = await post("/admin/master-data/solution-codes", {
    code: key,
    name: "Reconfigure QA",
  });
  const options = await (
    await page.request.get("/api/backend/categorization/options")
  ).json();
  const types = options.ticket_types as { id: number; name: string }[];
  expect(types.map((row) => row.name)).toEqual(
    expect.arrayContaining([
      "Issues",
      "Bugs",
      "Request",
      "Question",
      "Export Data",
      "Data Transfer",
      "Data Recovery",
      "Change Request",
    ]),
  );
  async function create(extra = {}) {
    return post("/tickets", {
      organization_id: org.id,
      product_instance_id: instanceA.id,
      subject: key,
      channel: "phone",
      ...extra,
    });
  }
  async function classification(id: number) {
    return (
      await page.request.get(`/api/backend/tickets/${id}/categorization`)
    ).json();
  }
  return {
    key,
    headers,
    post,
    create,
    classification,
    org,
    teacher,
    student,
    clinic,
    symptomA,
    symptomB,
    stageA,
    stageB,
    problemA,
    problemB,
    instanceA,
    instanceB,
    cause,
    solution,
    types,
    productA,
  };
}

for (const width of [1440, 390]) {
  test(`CAT-01/02/04/05/06/07: real capture, independent axes, product cascade, codes, audit and tag report at ${width}px`, async ({
    page,
    baseURL,
  }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const f = await setup(page, baseURL!);
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/cases/new");
    await page
      .getByRole("combobox", { name: "ลูกค้า / ผู้แจ้ง *" })
      .fill(f.key);
    await page
      .getByRole("option", { name: new RegExp(f.key) })
      .first()
      .click();
    await page.getByLabel("หัวข้อ *", { exact: true }).fill(`Capture ${f.key}`);
    await page.getByRole("button", { name: "โทรศัพท์", exact: true }).click();
    await page
      .locator(".capture-accordion")
      .first()
      .locator(":scope > summary")
      .click();
    await chooseOption(
      page,
      page.getByRole("combobox", {
        name: "ผลิตภัณฑ์ / ระบบที่ลูกค้าใช้งาน",
        exact: true,
      }),
      String(f.instanceA.id),
    );
    await choose(page, "ประเภทเคส", "Issues");
    await choose(page, "โมดูล (Module)", "Teacher");
    await choose(page, "อาการ", "Download failure");
    await choose(page, "ช่วงเวลาของการสอบ", "During exam");
    await choose(page, "ประเภทปัญหา", "Teacher access");
    await choose(page, "รหัสสาเหตุ", `${f.key} · Configuration QA`);
    await page
      .getByLabel("คำอธิบายสาเหตุ", { exact: true })
      .fill("Separate cause detail");
    await choose(page, "รหัสวิธีแก้", `${f.key} · Reconfigure QA`);
    await page
      .getByLabel("คำอธิบายวิธีแก้", { exact: true })
      .fill("Separate solution detail");
    await page.getByLabel("แท็กอิสระ", { exact: true }).fill(f.key);
    await page.getByRole("button", { name: "เพิ่มแท็ก", exact: true }).click();
    await page
      .getByLabel("แท็กอิสระ", { exact: true })
      .fill(f.key.toUpperCase());
    await page.getByRole("button", { name: "เพิ่มแท็ก", exact: true }).click();
    await expect(
      page.getByRole("button", { name: `ลบแท็ก ${f.key}`, exact: true }),
    ).toHaveCount(1);
    await expect(
      page.getByRole("status").filter({ hasText: "ไม่เพิ่มซ้ำ" }),
    ).toContainText(f.key);
    await page.getByRole("button", { name: "สร้างเคส", exact: true }).click();
    await expect(page).toHaveURL(/\/cases\/\d+$/);
    const id = Number(page.url().split("/").at(-1));
    const original = await (
      await page.request.get(`/api/backend/tickets/${id}`)
    ).json();
    let state = await f.classification(id);
    expect(state).toMatchObject({
      module_id: f.teacher.id,
      symptom_id: f.symptomA.id,
      service_stage_id: f.stageA.id,
      category_id: f.problemA.id,
      root_cause_code_id: f.cause.id,
      root_cause_detail: "Separate cause detail",
      resolution_code_id: f.solution.id,
      resolution_detail: "Separate solution detail",
      tags: [f.key],
    });
    await choose(page, "โมดูล (Module)", "Student");
    await saveCategories(page);
    state = await f.classification(id);
    expect(state).toMatchObject({
      module_id: f.student.id,
      symptom_id: f.symptomA.id,
      service_stage_id: f.stageA.id,
      category_id: null,
    });
    await choose(
      page,
      "ผลิตภัณฑ์ / ระบบที่ลูกค้าใช้งาน",
      "Instance B · 1 · production",
    );
    await expect(page.getByLabel("อาการ", { exact: true })).toContainText(
      "ยังไม่ระบุ",
    );
    await choose(page, "โมดูล (Module)", "Clinic");
    await choose(page, "อาการ", "Mapping error");
    await choose(page, "ช่วงเวลาของการสอบ", "General");
    await choose(page, "ประเภทปัญหา", "Clinic access");
    await saveCategories(page);
    await page.reload();
    await expect(
      page.getByLabel("โมดูล (Module)", { exact: true }),
    ).toContainText("Clinic");
    state = await f.classification(id);
    expect(state).toMatchObject({
      product_instance_id: f.instanceB.id,
      module_id: f.clinic.id,
      symptom_id: f.symptomB.id,
      service_stage_id: f.stageB.id,
    });
    const current = await (
      await page.request.get(`/api/backend/tickets/${id}`)
    ).json();
    for (const field of [
      "status",
      "ticket_no",
      "reported_at",
      "created_at",
      "owner_id",
    ])
      expect(current[field]).toBe(original[field]);
    const audit = await (
      await page.request.get(`/api/backend/tickets/${id}/audit`)
    ).json();
    expect(
      audit.some(
        (row: {
          changes: Record<string, { old: unknown; new: unknown }>;
          actor_id: number;
          created_at: string;
        }) =>
          row.changes.module_id?.old === f.teacher.id &&
          row.changes.module_id?.new === f.student.id &&
          row.actor_id === original.created_by_id &&
          !!row.created_at,
      ),
    ).toBe(true);
    await page
      .locator(".timeline-event.categorization_updated")
      .first()
      .getByText("ค่าเดิม / ค่าใหม่", { exact: true })
      .click();
    await expect(
      page.locator(".timeline-event.categorization_updated").first(),
    ).toContainText("โมดูล");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/cat-${width}.png`,
      fullPage: true,
    });
    if (width < 1000)
      await page
        .getByRole("button", { name: "เปิดหรือปิดเมนู", exact: true })
        .click();
    await page.getByRole("link", { name: "แท็กยอดนิยม", exact: true }).click();
    await expect(
      page.getByRole("row").filter({ hasText: f.key }),
    ).toContainText("1");
    await page.goto(`/cases/${id}`);
    await page
      .getByRole("button", { name: `ลบแท็ก ${f.key}`, exact: true })
      .click();
    await saveCategories(page);
    await page.goto("/reports/popular-tags");
    await expect(
      page.getByRole("heading", { name: "แท็กยอดนิยม", exact: true }),
    ).toBeVisible();
    await expect(page.getByRole("row").filter({ hasText: f.key })).toHaveCount(
      0,
    );
    expect(errors).toEqual([]);
  });
}

test("CAT master choices remain usable if product options fail", async ({
  page,
  baseURL,
}) => {
  const f = await setup(page, baseURL!);
  const ticket = await f.create();
  await page.route(
    `**/api/backend/products/${f.productA.id}/categorization-options`,
    (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Product options unavailable" }),
      }),
  );
  await page.goto(`/cases/${ticket.id}`);
  await expect(
    page.getByRole("alert").filter({ hasText: "Product options unavailable" }),
  ).toBeVisible();
  await choose(page, "ประเภทเคส", "Request");
  await choose(page, "รหัสสาเหตุ", `${f.key} · Configuration QA`);
  await expect(page.getByLabel("ประเภทเคส", { exact: true })).toContainText(
    "Request",
  );
});

test("CAT capture explains missing customer product configuration", async ({
  page,
  baseURL,
}) => {
  const f = await setup(page, baseURL!);
  const name = `${f.key}-unconfigured`;
  await f.post("/customers/organizations", { name });
  await page.goto("/cases/new");
  await page
    .locator(".capture-accordion")
    .first()
    .locator(":scope > summary")
    .click();
  await expect(
    page.getByText(
      "เลือกลูกค้า / ผู้แจ้งก่อน จึงจะเลือกระบบที่ลูกค้าใช้งานได้",
      { exact: true },
    ),
  ).toBeVisible();
  await page.getByRole("combobox", { name: "ลูกค้า / ผู้แจ้ง *" }).fill(name);
  await page
    .getByRole("option", { name: new RegExp(name) })
    .first()
    .click();
  await expect(
    page.getByText(
      "ลูกค้านี้ยังไม่มีผลิตภัณฑ์ / ระบบที่ผูกไว้ ให้ผู้ดูแลระบบเพิ่มระบบของลูกค้าก่อน",
      { exact: true },
    ),
  ).toBeVisible();
  await choose(page, "ประเภทเคส", "Request");
});

test("CAT-03: all eight SRS severity combinations and mandatory override reason through the UI", async ({
  page,
  baseURL,
}) => {
  const f = await setup(page, baseURL!);
  const ticket = await f.create();
  await page.goto(`/cases/${ticket.id}`);
  const matrix = [
    ["ทั้งองค์กร / ทั้งห้องสอบ", "ระหว่างสอบจริง", "S1"],
    ["ทั้งองค์กร / ทั้งห้องสอบ", "นอกช่วงสอบ", "S2"],
    ["บางกลุ่ม / บางรายวิชา", "ระหว่างสอบจริง", "S2"],
    ["บางกลุ่ม / บางรายวิชา", "นอกช่วงสอบ", "S3"],
    ["ผู้ใช้รายเดียว", "ระหว่างสอบจริง", "S3"],
    ["ผู้ใช้รายเดียว", "นอกช่วงสอบ", "S3"],
    ["คำถาม / คำขอที่ไม่กระทบการใช้งาน", "ระหว่างสอบจริง", "S3"],
    ["คำถาม / คำขอที่ไม่กระทบการใช้งาน", "นอกช่วงสอบ", "S4"],
  ];
  for (const [impact, time, expected] of matrix) {
    await choose(page, "ขอบเขตผลกระทบ", impact);
    await choose(page, "ช่วงเวลาที่เกิดเหตุ", time);
    await expect(page.getByLabel("Severity", { exact: true })).toContainText(
      `(${expected})`,
    );
    await saveCategories(page);
    expect((await f.classification(ticket.id)).severity).toBe(expected);
  }
  await choose(page, "ขอบเขตผลกระทบ", "ทั้งองค์กร / ทั้งห้องสอบ");
  await choose(page, "ช่วงเวลาที่เกิดเหตุ", "ระหว่างสอบจริง");
  await expect(page.getByLabel("Severity", { exact: true })).toContainText(
    "S1",
  );
  await choose(page, "Severity", "S4");
  const reason = page.getByLabel("เหตุผลที่ปรับ Severity", { exact: true });
  await expect(reason).toHaveAttribute("required", "");
  expect(
    await reason.evaluate((input) =>
      (input as HTMLInputElement).checkValidity(),
    ),
  ).toBe(false);
  await page
    .getByRole("button", { name: "บันทึกหมวดหมู่", exact: true })
    .click();
  expect((await f.classification(ticket.id)).impact_scope).toBe(
    "non_disruptive",
  );
  await reason.fill("Fallback service maintains operations");
  await saveCategories(page);
  expect(await f.classification(ticket.id)).toMatchObject({
    impact_scope: "organization",
    severity: "S4",
    severity_overridden_reason: "Fallback service maintains operations",
  });
});

test("CAT-02: Request uses its fulfilment workflow and existing CORE guards", async ({
  page,
  baseURL,
}) => {
  const f = await setup(page, baseURL!);
  const ticket = await f.create({
    module_id: f.teacher.id,
    category_id: f.problemA.id,
    root_cause_code_id: f.cause.id,
    resolution_code_id: f.solution.id,
  });
  await page.goto(`/cases/${ticket.id}`);
  await choose(page, "ประเภทเคส", "Request");
  await saveCategories(page);
  const request = page.locator(".request-workflow");
  await expect(request).toBeVisible();
  await request
    .getByLabel("ผู้ดำเนินคำขอ", { exact: true })
    .selectOption(String(ticket.created_by_id));
  await request
    .getByRole("button", { name: "เริ่มดำเนินคำขอ", exact: true })
    .click();
  await expect(
    request.getByRole("button", { name: "ส่งมอบผลคำขอ", exact: true }),
  ).toBeVisible();
  await request
    .getByLabel("ผลการส่งมอบคำขอ", { exact: true })
    .fill("Requested data delivered");
  await request
    .getByRole("button", { name: "ส่งมอบผลคำขอ", exact: true })
    .click();
  await expect(
    request.getByRole("button", { name: "ยืนยันและปิดคำขอ", exact: true }),
  ).toBeVisible();
  await request
    .getByRole("button", { name: "ยืนยันและปิดคำขอ", exact: true })
    .click();
  await expect(page.locator(".page-heading .case-status")).toContainText(
    "Closed",
  );
  expect(
    (await (await page.request.get(`/api/backend/tickets/${ticket.id}`)).json())
      .resolution_detail,
  ).toBe("Requested data delivered");
});

test("CAT-07: saved frequency is personal, product-scoped, and no-op saves do not inflate it", async ({
  page,
  baseURL,
}) => {
  const f = await setup(page, baseURL!);
  for (let index = 0; index < 3; index++)
    await f.create({ module_id: f.teacher.id });
  const ticket = await f.create();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/cases/${ticket.id}`);
  await expect(
    page.getByLabel("โมดูล (Module)", { exact: true }),
  ).not.toHaveAttribute("aria-disabled", "true");
  await page.getByLabel("โมดูล (Module)", { exact: true }).tap();
  const menu = page.getByRole("group", {
    name: "ตัวเลือกโมดูล (Module)",
    exact: true,
  });
  await expect(menu.getByRole("button").nth(1)).toHaveText("Teacher");
  await menu.getByRole("button", { name: "Teacher", exact: true }).tap();
  await saveCategories(page);
  const before = (
    await (
      await page.request.get(`/api/backend/tickets/${ticket.id}/audit`)
    ).json()
  ).length;
  await saveCategories(page);
  expect(
    (
      await (
        await page.request.get(`/api/backend/tickets/${ticket.id}/audit`)
      ).json()
    ).length,
  ).toBe(before);
  await login(page, baseURL!, "qa-agent");
  const own = await f.create();
  await page.goto(`/cases/${own.id}`);
  await expect(
    page.getByLabel("โมดูล (Module)", { exact: true }),
  ).not.toHaveAttribute("aria-disabled", "true");
  await page.getByLabel("โมดูล (Module)", { exact: true }).tap();
  await expect(menu.getByRole("button").nth(1)).toHaveText("Student");
  await menu.getByRole("button", { name: "Teacher", exact: true }).tap();
  expect(
    (
      await page.request.get("/api/backend/categorization/popular-tags")
    ).status(),
  ).toBe(403);
});
