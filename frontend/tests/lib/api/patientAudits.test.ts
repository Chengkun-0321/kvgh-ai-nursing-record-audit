import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
  type Mock,
} from "vitest";

import {
  ApiError,
  getAuditDays,
  runAudit,
  toErrorMessage,
} from "@/lib/api/patientAudits";

const DETAIL = "尚未設定使用中的模型，請至設定頁設定";

type FetchMock = Mock<typeof fetch>;
type FetchCall = { url: string; method: string; body: string };

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function describeCall(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<FetchCall> {
  if (input instanceof Request) {
    return {
      url: input.url,
      method: input.method,
      body: await input.clone().text(),
    };
  }
  const body = typeof init?.body === "string" ? init.body : "";
  return { url: input.toString(), method: init?.method ?? "GET", body };
}

async function firstCall(fetchMock: FetchMock): Promise<FetchCall> {
  const call = fetchMock.mock.calls[0];
  if (call === undefined) {
    throw new Error("fetch 沒有被呼叫");
  }
  return describeCall(call[0], call[1]);
}

async function captureError(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise;
  } catch (error) {
    return error;
  }
  throw new Error("預期請求失敗，但成功了");
}

function stubFetch(makeResponse: () => Response): FetchMock {
  const fetchMock: FetchMock = vi.fn<typeof fetch>(async () => makeResponse());
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  vi.stubEnv("API_BASE_URL", "http://backend.test");
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("getAuditDays", () => {
  it("B7／BR14：以經 URL 編碼的 patient_key 呼叫 audit-days", async () => {
    const fetchMock = stubFetch(() =>
      jsonResponse({ patient_key: "A病患", days: [] }),
    );
    const expectedSuffix = `/api/v1/patients/${encodeURIComponent("A病患")}/audit-days`;

    const result = await getAuditDays("A病患");

    const call = await firstCall(fetchMock);
    expect(call.url.endsWith(expectedSuffix)).toBe(true);
    expect(result.patient_key).toBe("A病患");
    expect(result.days).toEqual([]);
  });
});

describe("runAudit", () => {
  it("B7：以 POST 呼叫 /api/v1/audit-runs，body 帶 patient_key 與 business_date", async () => {
    const fetchMock = stubFetch(() => jsonResponse({}, 201));

    await runAudit("P001", "2026-09-02");

    const call = await firstCall(fetchMock);
    const body: unknown = JSON.parse(call.body);
    expect(call.url.endsWith("/api/v1/audit-runs")).toBe(true);
    expect(call.method.toUpperCase()).toBe("POST");
    expect(body).toMatchObject({
      patient_key: "P001",
      business_date: "2026-09-02",
    });
  });

  it("E12／B7：409 → reject ApiError，toErrorMessage 含後端的繁中 detail", async () => {
    stubFetch(() => jsonResponse({ detail: DETAIL }, 409));

    const error = await captureError(runAudit("P001", "2026-09-02"));

    expect(error).toBeInstanceOf(ApiError);
    expect(toErrorMessage(error)).toContain(DETAIL);
  });

  it("E12／B7：502 非 JSON 回應 → 也是 ApiError", async () => {
    stubFetch(() => new Response("Bad Gateway", { status: 502 }));

    const error = await captureError(runAudit("P001", "2026-09-02"));

    expect(error).toBeInstanceOf(ApiError);
    expect(toErrorMessage(error).length).toBeGreaterThan(0);
  });
});
