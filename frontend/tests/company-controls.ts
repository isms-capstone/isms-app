import { expect, type Locator, type Page } from "@playwright/test";
/** Select through the visible company menu, never mutate the hidden form control. */
export async function chooseOption(
  page: Page,
  control: Locator,
  option: string | { label: string },
) {
  const label =
    typeof option === "string"
      ? await control.evaluate((element, value) => {
          const native = element
            .closest(".company-select")
            ?.querySelector("select");
          return (
            Array.from(native?.options ?? [])
              .find((item) => item.value === value)
              ?.textContent?.trim() ?? value
          );
        }, option)
      : option.label;
  await control.click();
  await page.getByRole("option", { name: label, exact: true }).click();
  await expect(control).toHaveAttribute("aria-expanded", "false");
}
