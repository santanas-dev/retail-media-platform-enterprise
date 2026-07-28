import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import BriefListPage from "../pages/BriefListPage";
import BriefCreatePage from "../pages/BriefCreatePage";

const { mockGet, mockPost, mockRefresh, mockGetMe } = vi.hoisted(() => ({
    mockGet: vi.fn(),
    mockPost: vi.fn(),
    mockRefresh: vi.fn(),
    mockGetMe: vi.fn(),
}));

vi.mock("../api/client", () => ({
    api: {
        get: (...args: unknown[]) => mockGet(...args),
        login: vi.fn(),
        logout: vi.fn().mockResolvedValue(undefined),
        getMe: (...args: unknown[]) => mockGetMe(...args),
        post: (...args: unknown[]) => mockPost(...args),
        patch: vi.fn(),
        del: vi.fn(),
        refresh: (...args: unknown[]) => mockRefresh(...args),
    },
    setToken: vi.fn(),
    onUnauthorized: vi.fn(),
    ApiError: class extends Error {
        status: number;
        constructor(msg: string, status: number) {
            super(msg);
            this.status = status;
        }
    },
}));

function renderWithProviders(ui: React.ReactElement, { route = "/briefs" } = {}) {
    // Default: refresh succeeds + getMe returns advertiser user
    mockRefresh.mockResolvedValue({ access_token: "mock-token" });
    mockGetMe.mockResolvedValue({
        id: "u1",
        username: "advertiser_test",
        display_name: "Тестовый Рекламодатель",
        role_code: "advertiser",
    });
    return render(
        <MemoryRouter initialEntries={[route]}>
            <AuthProvider>{ui}</AuthProvider>
        </MemoryRouter>,
    );
}

describe("BriefListPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows empty state when no briefs", async () => {
        mockGet.mockResolvedValue({ items: [], total: 0 });
        renderWithProviders(<BriefListPage />);
        await waitFor(() => {
            expect(screen.getByTestId("brief-list-create-btn")).toBeDefined();
        });
        expect(screen.getByText("У вас пока нет заявок на размещение.")).toBeDefined();
    });

    it("shows brief cards with title and status", async () => {
        mockGet.mockResolvedValue({
            items: [{
                id: "b1", title: "Тестовый бриф", status: "submitted",
                product_category: "Молочка", budget_amount: 500000,
                budget_currency: "RUB", updated_at: "2026-07-22T12:00:00Z",
                created_at: "2026-07-22T10:00:00Z", organization_id: "org-1",
                created_by_id: "u1",
            }],
            total: 1,
        });
        renderWithProviders(<BriefListPage />);
        await waitFor(() => {
            expect(screen.getByText("Тестовый бриф")).toBeDefined();
        });
        expect(screen.getByText("Молочка")).toBeDefined();
    });

    it("shows error state", async () => {
        mockGet.mockRejectedValue(new Error("any"));
        renderWithProviders(<BriefListPage />);
        await waitFor(() => {
            expect(screen.getByText("Не удалось загрузить заявки")).toBeDefined();
        });
    });
});

describe("BriefCreatePage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders form with all fields and action buttons", () => {
        mockGet.mockResolvedValue({ items: [], total: 0 });
        renderWithProviders(<BriefCreatePage />, { route: "/briefs/new" });
        expect(screen.getByTestId("brief-create-title")).toBeDefined();
        expect(screen.getByTestId("brief-create-objective")).toBeDefined();
        expect(screen.getByTestId("brief-create-category")).toBeDefined();
        expect(screen.getByTestId("brief-create-budget")).toBeDefined();
        expect(screen.getByTestId("brief-create-channels")).toBeDefined();
        expect(screen.getByTestId("brief-create-comment")).toBeDefined();
        expect(screen.getByTestId("brief-create-draft")).toBeDefined();
        expect(screen.getByTestId("brief-create-submit")).toBeDefined();
    });

    it("shows validation error when title is empty on submit", async () => {
        const user = userEvent.setup();
        renderWithProviders(<BriefCreatePage />, { route: "/briefs/new" });
        await user.click(screen.getByTestId("brief-create-submit"));
        await waitFor(() => {
            expect(screen.getByText("Название заявки обязательно")).toBeDefined();
        });
    });

    it("creates and submits brief on submit click", async () => {
        mockPost.mockResolvedValueOnce({ id: "b-new", title: "Новый бриф", status: "draft" });
        mockPost.mockResolvedValueOnce({ id: "b-new", title: "Новый бриф", status: "submitted" });

        const user = userEvent.setup();
        renderWithProviders(<BriefCreatePage />, { route: "/briefs/new" });

        await user.type(screen.getByTestId("brief-create-title"), "Новый бриф");
        await user.click(screen.getByTestId("brief-create-submit"));

        await waitFor(() => {
            expect(mockPost).toHaveBeenCalledTimes(2);
        });
        // First call: create brief
        expect(mockPost).toHaveBeenNthCalledWith(1, "/campaign-briefs", expect.objectContaining({ title: "Новый бриф" }));
        // Second call: submit brief
        expect(mockPost).toHaveBeenNthCalledWith(2, "/campaign-briefs/b-new/submit");
    });
});
