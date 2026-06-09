import { describe, expect, it } from "vitest";
import { readErrorMessage } from "./client";

describe("readErrorMessage", () => {
  it("returns string detail", async () => {
    const response = new Response(JSON.stringify({ detail: "Rate limit exceeded" }), {
      status: 429,
    });
    await expect(readErrorMessage(response)).resolves.toBe("Rate limit exceeded");
  });

  it("returns nested message detail", async () => {
    const response = new Response(
      JSON.stringify({ detail: { message: "No valid log events found in file" } }),
      { status: 400 },
    );
    await expect(readErrorMessage(response)).resolves.toBe("No valid log events found in file");
  });

  it("falls back to status code", async () => {
    const response = new Response("not json", { status: 500 });
    await expect(readErrorMessage(response)).resolves.toBe("Request failed: 500");
  });
});
