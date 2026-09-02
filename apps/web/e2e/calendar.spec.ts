import { expect, test } from "@playwright/test";

test("dashboard and primary navigation are available", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name:/早上好/ })).toBeVisible();
  await expect(page.getByRole("heading", { name:"FOMC 利率决议" })).toBeVisible();
  await page.getByRole("link", { name:"今天", exact:true }).click();
  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByText(/API 实时数据/)).toBeVisible();
});

test("month view loads canonical events through the same-origin proxy", async ({ page }) => {
  await page.goto("/month");
  await expect(page.getByRole("heading", { name:"月历" })).toBeVisible();
  await expect(page.locator(".fc")).toBeVisible();
  await expect(page.getByText(/FOMC 利率决议/).first()).toBeVisible();
  const response = await page.request.get("/api/v1/events?limit=1");
  expect(response.ok()).toBeTruthy();
  expect((await response.json()).total).toBeGreaterThanOrEqual(57);
});

test("manual event drawer exposes precision and lock-safe editing fields", async ({ page }) => {
  await page.goto("/today");
  await page.getByRole("button", { name:"人工新增事件" }).click();
  await expect(page.getByRole("dialog", { name:"人工新增事件" })).toBeVisible();
  await expect(page.getByLabel("中文标题")).toBeVisible();
  await expect(page.getByLabel("时间精度")).toHaveValue("date");
  await expect(page.getByLabel("事件日期")).toHaveValue("2026-09-02");
  await page.getByRole("button", { name:"关闭" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});
