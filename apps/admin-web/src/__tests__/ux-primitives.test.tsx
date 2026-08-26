import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { useState } from "react";
import axe from "axe-core";

import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../theme/ThemeContext";
import Layout from "../components/Layout";
import PageHeader from "../components/PageHeader";
import FormField from "../components/FormField";
import TableControls from "../components/TableControls";
import { setViewportWidth, DESKTOP_WIDTH, MOBILE_WIDTH } from "./testMatchMedia";

/**
 * PORTAL-UX-POLISH-001A1a — the four shared primitives.
 *
 * PORTAL-UX-002 (sidebar eats 220px of a 390px screen), PORTAL-UX-003 (labels
 * that are visual only). The layout itself is CSS and is proven in the browser
 * matrix; what is proven here is the behaviour and the accessible semantics,
 * which is where the actual defects were.
 */

const LONG_TITLE =
  "Согласование кампаний рекламодателей с длинным названием раздела для проверки переноса";

const OPERATOR = {
  sub: "u-op",
  auth_provider: "local_break_glass",
  username: "operator",
  display_name: "Оператор Смены Длинное Имя",
  permissions: ["campaigns.read", "audit.read", "devices.read"],
};

function mockSession(me: Record<string, unknown> = OPERATOR) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }),
        { status: 200 }));
    }
    if (url.endsWith("/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify(me), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }));
  });
}

function renderShell(initialPath = "/campaigns") {
  const router = createMemoryRouter(
    [{
      path: "/",
      element: <Layout />,
      children: [
        { path: "campaigns", element: <div>содержимое кампаний</div> },
        { path: "audit", element: <div>журнал аудита</div> },
      ],
    }],
    { initialEntries: [initialPath] },
  );
  return render(
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ThemeProvider>,
  );
}

async function expectNoAxeViolations(container: HTMLElement, rules?: string[]) {
  const results = await axe.run(container, {
    runOnly: rules ? { type: "rule", values: rules } : undefined,
    // jsdom has no layout, so contrast cannot be evaluated here; it is checked
    // in the browser matrix instead.
    rules: { "color-contrast": { enabled: false } },
  });
  const summary = results.violations.map(
    (v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
  expect(summary).toEqual([]);
}

afterEach(() => {
  vi.restoreAllMocks();
  document.body.style.overflow = "";
});

// ── ResponsiveShell ─────────────────────────────────────────────────────────

describe("ResponsiveShell — desktop", () => {
  beforeEach(() => setViewportWidth(DESKTOP_WIDTH));

  it("shows the navigation without a menu trigger", async () => {
    mockSession();
    renderShell();
    expect(await screen.findByRole("link", { name: "Кампании" })).toBeInTheDocument();
    expect(screen.queryByTestId("nav-menu-toggle")).toBeNull();
    expect(screen.queryByTestId("nav-overlay")).toBeNull();
  });

  it("keeps the sidebar a plain landmark, not a dialog", async () => {
    mockSession();
    renderShell();
    await screen.findByRole("link", { name: "Кампании" });
    const sidebar = screen.getByTestId("nav-sidebar");
    expect(sidebar).not.toHaveAttribute("role", "dialog");
    expect(sidebar).not.toHaveAttribute("aria-hidden");
  });

  it("still filters navigation by permission (RBAC regression)", async () => {
    mockSession({ ...OPERATOR, permissions: ["campaigns.read"] });
    renderShell();
    expect(await screen.findByRole("link", { name: "Кампании" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Журнал аудита" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Пользователи" })).toBeNull();
  });

  it("keeps the theme switch reachable and labelled (regression)", async () => {
    mockSession();
    renderShell();
    await screen.findByRole("link", { name: "Кампании" });
    expect(screen.getByRole("radio", { name: "Тёмная тема" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Светлая тема" })).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    mockSession();
    const { container } = renderShell();
    await screen.findByRole("link", { name: "Кампании" });
    await expectNoAxeViolations(container);
  });
});

describe("ResponsiveShell — mobile 390px", () => {
  beforeEach(() => setViewportWidth(MOBILE_WIDTH));

  it("offers a labelled icon trigger and keeps the drawer closed initially", async () => {
    mockSession();
    renderShell();
    const trigger = await screen.findByTestId("nav-menu-toggle");
    expect(trigger).toHaveAccessibleName("Меню");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(trigger).toHaveAttribute("aria-controls", screen.getByTestId("nav-sidebar").id);
    expect(screen.getByTestId("nav-sidebar")).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByTestId("nav-overlay")).toBeNull();
  });

  it("opens the drawer, moves focus into it and locks body scroll", async () => {
    const user = userEvent.setup();
    mockSession();
    renderShell();
    const trigger = await screen.findByTestId("nav-menu-toggle");
    await user.click(trigger);

    const drawer = screen.getByTestId("nav-sidebar");
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(drawer).toHaveAttribute("role", "dialog");
    expect(drawer).toHaveAttribute("aria-modal", "true");
    expect(drawer).not.toHaveAttribute("aria-hidden");
    expect(document.body.style.overflow).toBe("hidden");
    await waitFor(() => expect(drawer).toContainElement(document.activeElement as HTMLElement));
  });

  it("closes on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    mockSession();
    renderShell();
    const trigger = await screen.findByTestId("nav-menu-toggle");
    await user.click(trigger);
    await user.keyboard("{Escape}");

    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("nav-sidebar")).toHaveAttribute("aria-hidden", "true");
    await waitFor(() => expect(document.activeElement).toBe(trigger));
    expect(document.body.style.overflow).toBe("");
  });

  it("closes on the overlay and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    mockSession();
    renderShell();
    const trigger = await screen.findByTestId("nav-menu-toggle");
    await user.click(trigger);
    await user.click(screen.getByTestId("nav-overlay"));

    expect(trigger).toHaveAttribute("aria-expanded", "false");
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("closes when a destination is chosen and navigates", async () => {
    const user = userEvent.setup();
    mockSession();
    renderShell();
    const trigger = await screen.findByTestId("nav-menu-toggle");
    await user.click(trigger);
    await user.click(screen.getByRole("link", { name: "Журнал аудита" }));

    expect(await screen.findByText("журнал аудита")).toBeInTheDocument();
    expect(trigger).toHaveAttribute("aria-expanded", "false");
  });

  it("reaches the drawer with the keyboard only", async () => {
    const user = userEvent.setup();
    mockSession();
    renderShell();
    const trigger = await screen.findByTestId("nav-menu-toggle");
    trigger.focus();
    await user.keyboard("{Enter}");
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    await waitFor(() =>
      expect(screen.getByTestId("nav-sidebar")).toContainElement(document.activeElement as HTMLElement));
  });

  it("has no axe violations with the drawer open", async () => {
    const user = userEvent.setup();
    mockSession();
    const { container } = renderShell();
    await user.click(await screen.findByTestId("nav-menu-toggle"));
    await expectNoAxeViolations(container);
  });
});

// ── PageHeader ──────────────────────────────────────────────────────────────

describe("PageHeader", () => {
  it("renders a single level-1 heading with the title", () => {
    render(<PageHeader title="Кампании" />);
    expect(screen.getByRole("heading", { level: 1, name: "Кампании" })).toBeInTheDocument();
  });

  it("renders subtitle, breadcrumbs and actions without a card wrapper", () => {
    const router = createMemoryRouter([{
      path: "/", element: (
        <PageHeader
          title="Карточка кампании"
          subtitle="Черновик"
          breadcrumbs={[{ label: "Кампании", to: "/campaigns" }, { label: "Карточка" }]}
        >
          <button type="button">Сохранить</button>
        </PageHeader>
      ),
    }], { initialEntries: ["/"] });
    render(<RouterProvider router={router} />);

    expect(screen.getByText("Черновик")).toBeInTheDocument();
    const crumbs = screen.getByTestId("page-header-breadcrumbs");
    expect(within(crumbs).getByRole("link", { name: "Кампании" })).toBeInTheDocument();
    expect(within(crumbs).getByText("Карточка")).toHaveAttribute("aria-current", "page");
    expect(within(screen.getByTestId("page-header-actions"))
      .getByRole("button", { name: "Сохранить" })).toBeInTheDocument();
  });

  it("keeps a long Russian title and its actions in separate containers", () => {
    render(
      <PageHeader title={LONG_TITLE}>
        <button type="button">Создать кампанию</button>
      </PageHeader>,
    );
    const heading = screen.getByRole("heading", { level: 1 });
    const actions = screen.getByTestId("page-header-actions");
    expect(heading.textContent).toBe(LONG_TITLE);
    expect(actions.contains(heading)).toBe(false);
    expect(heading.contains(actions)).toBe(false);
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <PageHeader title="Кампании" subtitle="Все кампании">
        <button type="button">Создать</button>
      </PageHeader>,
    );
    await expectNoAxeViolations(container);
  });
});

// ── FormField ───────────────────────────────────────────────────────────────

describe("FormField", () => {
  it("associates the label with the control it is given", () => {
    render(
      <FormField label="Сервер (LDAPS URL)">
        {(p) => <input {...p} type="text" />}
      </FormField>,
    );
    const input = screen.getByLabelText("Сервер (LDAPS URL)");
    expect(input).toBeInstanceOf(HTMLInputElement);
    expect(input.id).toBeTruthy();
  });

  it("works for select, textarea and a file trigger too", () => {
    render(
      <>
        <FormField label="Проверка сертификата">
          {(p) => <select {...p}><option value="a">A</option></select>}
        </FormField>
        <FormField label="Комментарий">{(p) => <textarea {...p} />}</FormField>
        <FormField label="Файл">{(p) => <input {...p} type="file" />}</FormField>
      </>,
    );
    expect(screen.getByLabelText("Проверка сертификата").tagName).toBe("SELECT");
    expect(screen.getByLabelText("Комментарий").tagName).toBe("TEXTAREA");
    expect(screen.getByLabelText("Файл")).toHaveAttribute("type", "file");
  });

  it("marks a required field in text as well as with an asterisk", () => {
    render(<FormField label="Название" required>{(p) => <input {...p} />}</FormField>);
    const input = screen.getByLabelText(/Название/);
    expect(input).toBeRequired();
    expect(input).toHaveAttribute("aria-required", "true");
    expect(screen.getByText("обязательное")).toBeInTheDocument();
  });

  it("describes the control with its help text", () => {
    render(
      <FormField label="Base DN" help="Корень каталога">
        {(p) => <input {...p} />}
      </FormField>,
    );
    expect(screen.getByLabelText("Base DN")).toHaveAccessibleDescription("Корень каталога");
  });

  it("exposes an error through aria-invalid, aria-describedby and an alert", () => {
    render(
      <FormField label="Base DN" error="Укажите Base DN">
        {(p) => <input {...p} />}
      </FormField>,
    );
    const input = screen.getByLabelText("Base DN");
    expect(input).toHaveAttribute("aria-invalid", "true");
    // The "!" mark is aria-hidden — it is there for sighted users, so the
    // error is not signalled by colour alone, and stays out of the announcement.
    expect(input).toHaveAccessibleDescription("Укажите Base DN");
    expect(screen.getByRole("alert")).toHaveTextContent("Укажите Base DN");
  });

  it("does not signal the error by colour alone", () => {
    render(<FormField label="Base DN" error="Укажите Base DN">{(p) => <input {...p} />}</FormField>);
    expect(screen.getByRole("alert").textContent).toContain("!");
  });

  it("reserves the error row so an error causes no layout shift", () => {
    const { rerender, container } = render(
      <FormField label="Base DN">{(p) => <input {...p} />}</FormField>,
    );
    const before = container.querySelector('[data-testid="form-field"]')!.childElementCount;
    rerender(<FormField label="Base DN" error="Укажите Base DN">{(p) => <input {...p} />}</FormField>);
    const after = container.querySelector('[data-testid="form-field"]')!.childElementCount;
    expect(after).toBe(before);
  });

  it("passes disabled and read-only through to the control", () => {
    render(
      <>
        <FormField label="Выключено" disabled>{(p) => <input {...p} />}</FormField>
        <FormField label="Только чтение" readOnly>{(p) => <input {...p} />}</FormField>
      </>,
    );
    expect(screen.getByLabelText("Выключено")).toBeDisabled();
    expect(screen.getByLabelText("Только чтение")).toHaveAttribute("readonly");
  });

  it("honours an id the page already owns", () => {
    render(<FormField label="Код" htmlFor="c-code">{(p) => <input {...p} />}</FormField>);
    expect(screen.getByLabelText("Код")).toHaveAttribute("id", "c-code");
  });

  it("has no axe violations, with and without an error", async () => {
    const { container, rerender } = render(
      <FormField label="Base DN" help="Корень каталога" required>
        {(p) => <input {...p} />}
      </FormField>,
    );
    await expectNoAxeViolations(container);
    rerender(
      <FormField label="Base DN" help="Корень каталога" required error="Укажите Base DN">
        {(p) => <input {...p} />}
      </FormField>,
    );
    await expectNoAxeViolations(container);
  });
});

// ── TableControls ───────────────────────────────────────────────────────────

function ControlledTableControls(props: { onSearch?: (v: string) => void }) {
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("name");
  return (
    <TableControls
      search={{
        value: q,
        onChange: (v) => { setQ(v); props.onSearch?.(v); },
        placeholder: "Код или название",
      }}
      sort={{
        value: sort,
        options: [{ value: "name", label: "По названию" }, { value: "date", label: "По дате" }],
        onChange: setSort,
      }}
      resultLabel={`Показано 3 из 42`}
      onReset={() => { setQ(""); setSort("name"); }}
      canReset={q !== "" || sort !== "name"}
    />
  );
}

describe("TableControls", () => {
  it("labels every control it renders", () => {
    render(<ControlledTableControls />);
    expect(screen.getByLabelText("Поиск")).toBeInTheDocument();
    expect(screen.getByLabelText("Сортировка")).toBeInTheDocument();
  });

  it("reports typing to the page rather than filtering anything itself", async () => {
    const user = userEvent.setup();
    const onSearch = vi.fn();
    render(<ControlledTableControls onSearch={onSearch} />);
    await user.type(screen.getByLabelText("Поиск"), "смоук");
    expect(onSearch).toHaveBeenCalled();
    expect(onSearch.mock.calls.at(-1)![0]).toBe("смоук");
  });

  it("reports a sort choice to the page", async () => {
    const user = userEvent.setup();
    render(<ControlledTableControls />);
    await user.selectOptions(screen.getByLabelText("Сортировка"), "date");
    expect((screen.getByLabelText("Сортировка") as HTMLSelectElement).value).toBe("date");
  });

  it("enables reset only once something is filtered, and clears it", async () => {
    const user = userEvent.setup();
    render(<ControlledTableControls />);
    const reset = screen.getByTestId("table-controls-reset");
    expect(reset).toBeDisabled();
    await user.type(screen.getByLabelText("Поиск"), "x");
    expect(reset).toBeEnabled();
    await user.click(reset);
    expect((screen.getByLabelText("Поиск") as HTMLInputElement).value).toBe("");
  });

  it("disables its controls while loading and says so", () => {
    render(
      <TableControls
        search={{ value: "", onChange: () => {} }}
        resultLabel="Показано 3 из 42"
        onReset={() => {}}
        loading
      />,
    );
    expect(screen.getByLabelText("Поиск")).toBeDisabled();
    expect(screen.getByTestId("table-controls-reset")).toBeDisabled();
    expect(screen.getByTestId("table-controls-count")).toHaveTextContent("Загрузка…");
  });

  it("renders no search box when the page cannot honestly search", () => {
    render(
      <TableControls
        filters={<button type="button">Черновики</button>}
        resultLabel="12 из 50 на этой странице"
        scopeNote="Фильтр применяется к загруженной странице"
      />,
    );
    expect(screen.queryByTestId("table-controls-search")).toBeNull();
    expect(screen.getByTestId("table-controls-scope"))
      .toHaveTextContent("Фильтр применяется к загруженной странице");
  });

  it("has no axe violations", async () => {
    const { container } = render(<ControlledTableControls />);
    await expectNoAxeViolations(container);
  });
});
