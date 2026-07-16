import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import ApplyAdvertiserPage from "../pages/ApplyAdvertiserPage";

function createRouter() {
  return createMemoryRouter(
    [
      {
        path: "/become-advertiser",
        element: <ApplyAdvertiserPage />,
      },
    ],
    { initialEntries: ["/become-advertiser"] },
  );
}

function renderPage() {
  const router = createRouter();
  return render(<RouterProvider router={router} />);
}

describe("apply advertiser page — client validation", () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it("shows validation errors for empty required fields", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByText("Отправить заявку"));

    await waitFor(() => {
      const requiredFields = screen.getAllByText("Обязательное поле");
      expect(requiredFields.length).toBe(3); // company_name, contact_name, email
      expect(screen.getByText("Необходимо согласие на обработку данных")).toBeTruthy();
    });
  });

  it("shows consent validation when unchecked", async () => {
    const user = userEvent.setup();
    renderPage();

    // Fill required fields but not consent
    await user.type(screen.getByPlaceholderText("ООО Ромашка"), "Тест");
    await user.type(screen.getByPlaceholderText("Иванов Иван"), "Иван");
    await user.type(screen.getByPlaceholderText("ivan@example.com"), "i@t.ru");
    await user.click(screen.getByText("Отправить заявку"));

    await waitFor(() => {
      expect(screen.getByText("Необходимо согласие на обработку данных")).toBeTruthy();
    });
  });
});

describe("apply advertiser page — success submit", () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it("submits successfully and shows no-immediate-access text", async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          id: "app-001",
          company_name: "ООО Тест",
          contact_name: "Иван",
          email: "i@t.ru",
          phone: "",
          website: "",
          comment: "",
          consent: true,
          status: "new",
          reviewer_id: null,
          review_reason: null,
          reviewed_at: null,
          created_at: "2026-07-17T10:00:00Z",
          updated_at: "2026-07-17T10:00:00Z",
        }),
        { status: 201 },
      ),
    );

    renderPage();

    await user.type(screen.getByPlaceholderText("ООО Ромашка"), "ООО Тест");
    await user.type(screen.getByPlaceholderText("Иванов Иван"), "Иван");
    await user.type(screen.getByPlaceholderText("ivan@example.com"), "i@t.ru");

    const consentCheckbox = screen.getByLabelText(/согласие на обработку/i);
    await user.click(consentCheckbox);

    await user.click(screen.getByText("Отправить заявку"));

    await waitFor(() => {
      expect(screen.getByText("Заявка отправлена")).toBeTruthy();
    });

    // Proof: success text explicitly states no immediate access
    const body = document.body.textContent || "";
    expect(body).toMatch(/не даёт немедленного доступа/i);
    expect(body).toMatch(/заявка проходит проверку/i);
  });
});

describe("apply advertiser page — server error", () => {
  beforeEach(() => { vi.restoreAllMocks(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it("shows server error on failure", async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Сервер временно недоступен" }),
        { status: 500 },
      ),
    );

    renderPage();

    await user.type(screen.getByPlaceholderText("ООО Ромашка"), "ООО Тест");
    await user.type(screen.getByPlaceholderText("Иванов Иван"), "Иван");
    await user.type(screen.getByPlaceholderText("ivan@example.com"), "i@t.ru");

    const consentCheckbox = screen.getByLabelText(/согласие на обработку/i);
    await user.click(consentCheckbox);

    await user.click(screen.getByText("Отправить заявку"));

    await waitFor(() => {
      expect(screen.getByText("Сервер временно недоступен")).toBeTruthy();
    });
  });

  it("shows 429 rate limit error", async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({ detail: "Too many requests" }),
        { status: 429 },
      ),
    );

    renderPage();

    await user.type(screen.getByPlaceholderText("ООО Ромашка"), "ООО Тест");
    await user.type(screen.getByPlaceholderText("Иванов Иван"), "Иван");
    await user.type(screen.getByPlaceholderText("ivan@example.com"), "i@t.ru");

    const consentCheckbox = screen.getByLabelText(/согласие на обработку/i);
    await user.click(consentCheckbox);

    await user.click(screen.getByText("Отправить заявку"));

    await waitFor(() => {
      expect(screen.getByText("Too many requests")).toBeTruthy();
    });
  });
});
