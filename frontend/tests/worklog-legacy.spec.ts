import { test, expect } from "@playwright/test";

test("backend plain-text 500 preserves the draft and a later retry saves once", async ({
  page,
  baseURL,
}) => {
  test.skip(
    process.env.WRK_LEGACY_QA !== "1",
    "Requires the disposable legacy-contract QA server",
  );
  const headers = { origin: baseURL! };
  await page.request.post("/api/session", {
    headers,
    data: { username: "qa-admin", password: "test-only-password" },
  });
  await page.request.post("/api/backend/qa/reset", { headers });
  await page.goto("/cases/1");
  await expect(
    page.getByRole("heading", { name: "DVHT-QA-00001" }),
  ).toBeVisible();
  await page.request.post("/api/backend/qa/fail-next", { headers });
  const composer = page.locator(".worklog-panel .worklog-composer");
  const text = composer.getByLabel("ข้อความ *", { exact: true });
  await text.fill("Draft survives backend error");
  const response = page.waitForResponse(
    (value) =>
      value.request().method() === "POST" &&
      value.url().endsWith("/tickets/1/worklogs"),
  );
  await composer
    .getByRole("button", { name: "บันทึกข้อความ", exact: true })
    .click();
  expect((await response).status()).toBe(500);
  await expect(
    page.getByRole("alert").filter({ hasText: "HTTP 500" }),
  ).toBeVisible();
  await expect(text).toHaveValue("Draft survives backend error");
  await expect(page.locator(".timeline-event")).toHaveCount(0);
  await composer
    .getByRole("button", { name: "บันทึกข้อความ", exact: true })
    .click();
  await expect(page.locator(".timeline-event.internal_note")).toHaveCount(1);
  await expect(page.locator(".timeline-event.internal_note")).toContainText(
    "Draft survives backend error",
  );
});

test("legacy backend: save Internal Note and LINE OA reply, update immediately and persist after reload", async ({
  page,
  baseURL,
}) => {
  test.skip(
    process.env.WRK_LEGACY_QA !== "1",
    "Requires the disposable legacy-contract QA server",
  );
  const failures: string[] = [];
  page.on("response", (response) => {
    if (
      /\/api\/backend\/tickets\/1\/(categorization|timeline|worklogs)/.test(
        response.url(),
      ) &&
      response.status() >= 400
    )
      failures.push(`${response.status()} ${response.url()}`);
  });
  await page.request.post("/api/session", {
    headers: { origin: baseURL! },
    data: { username: "qa-admin", password: "test-only-password" },
  });
  await page.request.post("/api/backend/qa/reset", {
    headers: { origin: baseURL! },
  });
  await page.goto("/cases/1");
  await expect(
    page.getByRole("heading", { name: "DVHT-QA-00001" }),
  ).toBeVisible();
  const composer = page.locator(".worklog-panel .worklog-composer");
  await composer
    .getByLabel("ข้อความ *", { exact: true })
    .fill("Internal Note realtime QA");
  await composer
    .getByRole("button", { name: "บันทึกข้อความ", exact: true })
    .click();
  await expect(page.locator(".timeline-event.internal_note")).toContainText(
    "Internal Note realtime QA",
  );
  await expect(
    page.locator(".timeline-event.internal_note .delivery-channel"),
  ).toHaveCount(0);
  await composer
    .getByRole("button", { name: "Public Reply", exact: true })
    .click();
  await composer
    .getByLabel("ช่องทางที่ส่งจริง *", { exact: true })
    .selectOption("line_oa");
  await composer
    .getByLabel("ข้อความ *", { exact: true })
    .fill("Public Reply LINE OA QA");
  await composer
    .getByRole("button", { name: "บันทึกข้อความ", exact: true })
    .click();
  const reply = page.locator(".timeline-event.public_reply");
  await expect(reply).toContainText("Public Reply LINE OA QA");
  await expect(reply.locator(".delivery-channel")).toHaveText(
    "ส่งจริงผ่าน LINE OA",
  );
  await expect(reply).toHaveCSS("border-left-color", "rgb(115, 232, 175)");
  await page.reload();
  await expect(page.locator(".timeline-event.internal_note")).toContainText(
    "Internal Note realtime QA",
  );
  await expect(page.locator(".timeline-event.public_reply")).toContainText(
    "ส่งจริงผ่าน LINE OA",
  );
  const records = await (
    await page.request.get("/api/backend/tickets/1/worklogs")
  ).json();
  expect(records).toHaveLength(2);
  expect(records[0]).toMatchObject({
    message: "Internal Note realtime QA",
    is_internal: true,
  });
  expect(records[1]).toMatchObject({
    message: "Public Reply LINE OA QA",
    is_internal: false,
    channel: "line_oa",
  });
  expect(failures).toEqual([]);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/worklog-legacy-mobile.png",
    fullPage: true,
  });
});

test("newly saved worklogs stay visible beyond the first timeline page without duplicates", async ({
  page,
  baseURL,
}) => {
  test.skip(
    process.env.WRK_LEGACY_QA !== "1",
    "Requires the disposable legacy-contract QA server",
  );
  const headers = { origin: baseURL! };
  await page.request.post("/api/session", {
    headers,
    data: { username: "qa-admin", password: "test-only-password" },
  });
  await page.request.post("/api/backend/qa/seed", { headers });
  await page.goto("/cases/1");
  await expect(page.locator(".timeline-event")).toHaveCount(100);
  const composer = page.locator(".worklog-panel .worklog-composer");
  await composer
    .getByLabel("ข้อความ *", { exact: true })
    .fill("Newest past page 1");
  await composer
    .getByRole("button", { name: "บันทึกข้อความ", exact: true })
    .click();
  await expect(
    page.getByText("Newest past page 1", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "โหลดเหตุการณ์เพิ่มเติม", exact: true })
    .click();
  await expect(page.locator(".timeline-event")).toHaveCount(106);
  await expect(
    page.getByText("Newest past page 1", { exact: true }),
  ).toHaveCount(1);
  await expect(page.getByText("Seed 100", { exact: true })).toBeVisible();
});
