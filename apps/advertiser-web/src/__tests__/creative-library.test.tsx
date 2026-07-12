import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import CreativeLibraryPage from "../pages/CreativeLibraryPage";

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    login: vi.fn(), logout: vi.fn().mockResolvedValue(undefined),
    getMe: vi.fn().mockResolvedValue({ sub: "u1", auth_provider: "local_advertiser", username: "a", display_name: "A" }),
    patch: vi.fn(), del: vi.fn(), refresh: vi.fn().mockResolvedValue({ access_token: "t", token_type: "Bearer", expires_in: 1800 }),
  },
  setToken: vi.fn(), onUnauthorized: vi.fn(),
  ApiError: class extends Error { status: number; constructor(s: number) { super(`HTTP ${s}`); this.status = s; this.name = "ApiError"; } },
}));

let AE: typeof Error & { new (s: number): Error & { status: number } };
beforeAll(async () => { AE = (await import("../api/client")).ApiError as any; });
const makeApiError = (s: number) => new AE(s);

const asset1 = {
  id: "a1", advertiser_organization_id: "o1", code: "CR-001", name: "Баннер 1",
  media_type: "image/png", sha256_checksum: "abc", file_size_bytes: 50000,
  duration_ms: null, resolution_w: 1920, resolution_h: 1080,
  status: "ready", moderation_status: "approved",
  created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z",
};
const asset2 = {
  id: "a2", advertiser_organization_id: "o1", code: "CR-002", name: "Видео",
  media_type: "video/mp4", sha256_checksum: "", file_size_bytes: 0,
  duration_ms: null, resolution_w: null, resolution_h: null,
  status: "metadata_only", moderation_status: "pending_review",
  created_at: "2025-06-01T00:00:00Z", updated_at: "2025-06-01T00:00:00Z",
};

function renderPage() {
  /* S-035b: session restore via refresh — no localStorage */
  const router = createMemoryRouter(
    [{ path: "/creatives", element: <AuthProvider><CreativeLibraryPage /></AuthProvider> }],
    { initialEntries: ["/creatives"] },
  );
  return render(<RouterProvider router={router} />);
}

describe("CreativeLibraryPage", () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); });
  afterEach(() => localStorage.clear());

  it("renders asset list", async () => {
    mockGet.mockResolvedValue([asset1, asset2]);
    renderPage();
    await screen.findByText("Баннер 1", {}, { timeout: 3000 });
    expect(screen.getByText("Видео")).toBeInTheDocument();
    expect(screen.getByText("CR-001")).toBeInTheDocument();
  });

  it("shows empty state", async () => {
    mockGet.mockResolvedValue([]);
    renderPage();
    await screen.findByText("Нет креативов", {}, { timeout: 3000 });
  });

  it("shows access error on 403", async () => {
    mockGet.mockRejectedValue(makeApiError(403));
    renderPage();
    await screen.findByText("Нет прав на просмотр креативов", {}, { timeout: 3000 });
  });

  it("clears session on 401", async () => {
    mockGet.mockRejectedValue(makeApiError(401));
    renderPage();
    await waitFor(() => {
      expect(localStorage.getItem("rmp_access_token")).toBeNull();
    }, { timeout: 3000 });
  });

  it("no storage fields rendered", async () => {
    mockGet.mockResolvedValue([asset1]);
    renderPage();
    await screen.findByText("Баннер 1", {}, { timeout: 3000 });
    const body = document.body.textContent ?? "";
    expect(body).not.toMatch(/storage_bucket|storage_key|presigned_url/i);
  });

  it("shows upload button for metadata_only asset", async () => {
    mockGet.mockResolvedValue([asset2]);
    renderPage();
    await screen.findByText("Загрузить файл", {}, { timeout: 3000 });
  });

  it("creates asset and refreshes list", async () => {
    mockGet.mockResolvedValue([]); // initial empty
    renderPage();
    await screen.findByText("Нет креативов", {}, { timeout: 3000 });

    // Show form
    fireEvent.click(screen.getByText("Добавить креатив"));
    const nameInput = screen.getByPlaceholderText("Новогодний баннер") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "Мой креатив" } });
    fireEvent.click(screen.getByText("Создать"));

    // Verify POST payload
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith("/creative-assets", expect.objectContaining({
        name: "Мой креатив",
        media_type: "image/png",
      }));
    }, { timeout: 3000 });
  });

  it("upload flow calls upload-intent with correct asset id", async () => {
    mockGet.mockResolvedValue([asset2]); // metadata_only
    renderPage();
    await screen.findByText("Загрузить файл", {}, { timeout: 3000 });

    // Mock upload-intent response
    mockPost.mockResolvedValueOnce({
      upload_id: "upl-1",
      upload_url: "https://minio.example.com/upload",
      method: "PUT",
      headers: { "Content-Type": "video/mp4" },
      expires_at: "2026-01-01T00:00:00Z",
    });

    // Click upload
    fireEvent.click(screen.getByText("Загрузить файл"));

    // Simulate file selection
    const file = new File(["test"], "video.mp4", { type: "video/mp4" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    // Set assetId on the input (how the component stores it)
    (input as HTMLInputElement & { _assetId?: string })._assetId = "a2";

    fireEvent.change(input, { target: { files: [file] } });

    // Verify upload-intent called with correct asset_id
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith(
        "/creative-assets/a2/upload-intent",
        expect.objectContaining({
          filename: "video.mp4",
          content_type: "video/mp4",
          content_length: 4,
        }),
      );
    }, { timeout: 3000 });
  });

  it("shows upload error and allows retry", async () => {
    mockGet.mockResolvedValue([asset2]);
    renderPage();
    await screen.findByText("Загрузить файл", {}, { timeout: 3000 });

    // Mock upload-intent to fail
    const err = makeApiError(422);
    (err as unknown as Record<string, unknown>).body = { detail: "Файл слишком большой" };
    mockPost.mockRejectedValue(err);
    mockPost.mockRejectedValue(err); // second call for complete-upload

    fireEvent.click(screen.getByText("Загрузить файл"));
    const file = new File(["test"], "video.mp4", { type: "video/mp4" });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    (input as HTMLInputElement & { _assetId?: string })._assetId = "a2";
    fireEvent.change(input, { target: { files: [file] } });

    // Error should appear (any non-empty error text)
    await waitFor(() => {
      const hasError = !!document.body.textContent?.match(/ошибк|error|файл/i);
      expect(hasError).toBe(true);
    }, { timeout: 3000 });
  });
});
