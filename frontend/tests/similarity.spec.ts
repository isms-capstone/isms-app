import { test, expect, type Page } from "@playwright/test";

const instance = {
  id: 1,
  product_id: 1,
  name: "Exam",
  version: "1",
  environment: "production",
};
const organization = { id: 1, name: "QA Customer", is_active: true };
const suggestion = {
  id: 12,
  ticket_no: "DVHT-QA-12",
  subject: "Existing login issue",
  status: "CLOSED",
  hint: "เคยแก้แล้ว มีวิธีแก้",
  score: 90,
  customer: "QA Customer",
  product: "Exam",
  product_id: 1,
  product_instance_id: 1,
  module_id: 2,
  category_id: 3,
  severity: "S2",
  impact_scope: "organization",
  is_exam_window: false,
  severity_overridden_reason: null,
  resolution_code_id: null,
  resolution_detail: "Sign in again",
  source_type: "ticket",
  assignee: "QA Agent",
  last_activity: "2026-11-03T00:00:00Z",
};

async function setup(page: Page, slow = false) {
  const searches: string[] = [];
  const decisions: unknown[] = [];
  const creates: Record<string, unknown>[] = [];
  await page.route("**/api/backend/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace("/api/backend", "");
    let json: unknown = [];
    if (path === "/registry/session")
      json = {
        id: 1,
        username: "qa",
        role: "Admin",
        can_create_cases: true,
        can_edit_customers: true,
        can_edit_products: true,
      };
    else if (path === "/customers/autocomplete")
      json = [{ organization, contact: null }];
    else if (path.endsWith("/selection-context"))
      json = {
        organization,
        contact: null,
        instances: [instance],
        departments: [],
        courses: [],
      };
    else if (path === "/product-instances") json = [instance];
    else if (path === "/categorization/options")
      json = { ticket_types: [], causes: [], solutions: [] };
    else if (
      path.endsWith("/case-options") ||
      path.endsWith("/categorization-options")
    )
      json = {
        modules: [{ id: 2, name: "Login" }],
        problem_types: [{ id: 3, name: "Sign in", module_id: 2 }],
        symptoms: [],
        service_stages: [],
        ticket_types: [],
        causes: [],
        solutions: [],
      };
    else if (path === "/categorization/severity-suggestion")
      json = { severity: "S2", is_exam_window: false };
    else if (path === "/tickets/similar") {
      searches.push(url.searchParams.get("q") || "");
      if (slow) await new Promise((resolve) => setTimeout(resolve, 2300));
      json = {
        feedback_id: 7,
        items: [suggestion],
        decision_required: true,
        available: true,
      };
    } else if (path.startsWith("/tickets/similarity-feedback/")) {
      decisions.push(route.request().postDataJSON());
      json = {
        feedback_id: 7,
        reuse_values: route.request().postDataJSON().reuse_values,
      };
    } else if (path === "/tickets" && route.request().method() === "POST") {
      creates.push(route.request().postDataJSON());
      json = { id: 99 };
    }
    await route.fulfill({ status: 200, json }).catch(() => {});
  });
  await page.goto("/cases/new");
  await page.getByRole("combobox").first().fill("QA");
  await page.getByRole("option", { name: /QA Customer/ }).click();
  await page.getByRole("button", { name: "โทรศัพท์", exact: true }).click();
  return { searches, decisions, creates };
}

test("SIM debounce and required decision persist with the new case", async ({
  page,
}) => {
  const state = await setup(page);
  const subject = page.getByLabel("หัวข้อ *", { exact: true });
  await subject.fill("123456789");
  await page.waitForTimeout(600);
  expect(state.searches).toHaveLength(0);
  await subject.fill("Login error 12345");
  await page.waitForTimeout(200);
  expect(state.searches).toHaveLength(0);
  await expect(
    page.getByText("Existing login issue", { exact: false }),
  ).toBeVisible();
  expect(state.searches).toHaveLength(1);
  await expect(
    page.getByRole("button", { name: "สร้างเคส", exact: true }),
  ).toBeDisabled();
  await page
    .getByRole("radio", { name: "เปิดสอบสวนใหม่", exact: true })
    .check();
  await page.getByRole("button", { name: "ยืนยันการเลือก" }).click();
  await expect(
    page.getByRole("button", { name: "สร้างเคส", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "สร้างเคส", exact: true }).click();
  await expect.poll(() => state.creates.length).toBe(1);
  expect(state.creates[0].similarity_feedback_id).toBe(7);
  expect(state.decisions[0]).toMatchObject({
    decision: "new",
    chosen_ticket_id: null,
  });
});

test("SIM times out silently after 1.5 seconds and releases case capture", async ({
  page,
}) => {
  const state = await setup(page, true);
  await page.getByLabel("หัวข้อ *", { exact: true }).fill("Login error 12345");
  await expect.poll(() => state.searches.length).toBe(1);
  await expect(
    page.getByRole("button", { name: "สร้างเคส", exact: true }),
  ).toBeEnabled({ timeout: 2000 });
  await expect(page.getByText("90%", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("region", { name: "เคสที่คล้ายกัน" }).getByRole("alert"),
  ).toHaveCount(0);
});

test("SIM reuse fills editable fields and submits the edited solution", async ({
  page,
}) => {
  const state = await setup(page);
  await page.getByLabel("หัวข้อ *", { exact: true }).fill("Login error 12345");
  await page.getByRole("radio", { name: "เลือกเคสนี้" }).check();
  await page
    .getByRole("radio", { name: "ใช้วิธีแก้เดิม", exact: true })
    .check();
  await expect(
    page.getByRole("textbox", { name: "ขั้นตอนการแก้", exact: true }),
  ).toHaveValue("Sign in again");
  await page
    .getByRole("textbox", { name: "ขั้นตอนการแก้", exact: true })
    .fill("Edited solution");
  await page.getByRole("button", { name: "ยืนยันการเลือก" }).click();
  await expect(
    page.getByRole("button", { name: "สร้างเคส", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "สร้างเคส", exact: true }).click();
  await expect.poll(() => state.creates.length).toBe(1);
  expect(state.creates[0]).toMatchObject({
    similarity_feedback_id: 7,
    severity: "S2",
    resolution_detail: "Edited solution",
    category_id: 3,
  });
});
