/**
 * ADVERTISER-UX-001D2 — Permission descriptions registry.
 *
 * Единый источник человекочитаемых описаний прав (permissions).
 * Ключ = permission code (seed/permissions.code).
 *
 * Формат: { code: string, name: string, description: string }
 *
 * Неизвестные permissions падают безопасно:
 *   label = code, description = «Описание права пока не задано»
 */

export interface PermissionDescription {
  code: string;
  /** Human-readable label (совпадает с seed permissions.name) */
  name: string;
  /** Человекочитаемое описание — что оператор реально может делать */
  description: string;
}

const REGISTRY: Record<string, Omit<PermissionDescription, "code">> = {
  "users.read": {
    name: "Просмотр пользователей",
    description: "Видеть список пользователей, их роли, статусы и провайдеры аутентификации",
  },
  "users.manage": {
    name: "Управление пользователями",
    description: "Создавать локальных рекламодателей, деактивировать/активировать пользователей, сбрасывать пароли",
  },
  "roles.read": {
    name: "Просмотр ролей",
    description: "Видеть список ролей и назначенные пользователям роли",
  },
  "roles.manage": {
    name: "Управление ролями",
    description: "Назначать и снимать роли с пользователей",
  },
  "audit.read": {
    name: "Просмотр аудита",
    description: "Видеть журнал аудита действий в системе",
  },
  "organization.read": {
    name: "Просмотр организации",
    description: "Видеть данные торговой сети (ритейлера)",
  },
  "channels.read": {
    name: "Просмотр каналов",
    description: "Видеть каналы размещения рекламы (магазины, дисплеи, зоны)",
  },
  "devices.read": {
    name: "Просмотр устройств",
    description: "Видеть список KSO-устройств, их статус и состояние здоровья",
  },
  "emergency.read": {
    name: "Просмотр аварийного режима",
    description: "Видеть статус аварийного режима сети",
  },
  "emergency.manage": {
    name: "Управление аварийным режимом",
    description: "Включать и выключать аварийный режим для всей сети устройств",
  },
  "advertiser_applications.read": {
    name: "Просмотр заявок рекламодателей",
    description: "Видеть заявки от рекламодателей на регистрацию в платформе",
  },
  "advertiser_applications.review": {
    name: "Рассмотрение заявок рекламодателей",
    description: "Одобрять или отклонять заявки рекламодателей на регистрацию",
  },
  "advertisers.read": {
    name: "Просмотр рекламодателей",
    description: "Видеть список организаций рекламодателей, их бренды, договоры и контакты",
  },
  "advertisers.manage": {
    name: "Управление рекламодателями",
    description: "Создавать и редактировать организации рекламодателей, реквизиты и приглашения",
  },
  "advertisers.contacts.read": {
    name: "Просмотр контактов рекламодателей",
    description: "Видеть контактных лиц рекламодателей",
  },
  "advertisers.contacts.manage": {
    name: "Управление контактами рекламодателей",
    description: "Добавлять и редактировать контактных лиц рекламодателей",
  },
  "campaigns.read": {
    name: "Просмотр кампаний",
    description: "Видеть список рекламных кампаний, их статусы и вложения",
  },
  "campaigns.manage": {
    name: "Управление кампаниями",
    description: "Создавать и редактировать рекламные кампании, флайты и размещения",
  },
  "campaigns.approve": {
    name: "Согласование кампаний",
    description: "Утверждать или отклонять рекламные кампании перед запуском",
  },
  "creatives.read": {
    name: "Просмотр креативов",
    description: "Видеть загруженные рекламные материалы (креативы)",
  },
  "creatives.moderate": {
    name: "Модерация креативов",
    description: "Одобрять или отклонять рекламные креативы по содержанию и техническим требованиям",
  },
  "inventory.read": {
    name: "Просмотр инвентаря",
    description: "Видеть доступный рекламный инвентарь и занятость слотов",
  },
  "inventory.manage": {
    name: "Управление инвентарём",
    description: "Создавать и редактировать правила размещения и симулировать занятость",
  },
};

const FALLBACK: Omit<PermissionDescription, "code"> = {
  name: "",
  description: "Описание права пока не задано",
};

/**
 * Get label + description for a permission code.
 * Unknown codes fall back safely.
 */
export function getPermissionDescription(code: string): PermissionDescription {
  const entry = REGISTRY[code];
  if (entry) {
    return { code, ...entry };
  }
  return {
    code,
    name: code, // show code as label for unknown perms
    description: FALLBACK.description,
  };
}

/** All registered permission codes (for catalog display). */
export const ALL_PERMISSION_CODES: string[] = Object.keys(REGISTRY);

export { REGISTRY as _REGISTRY };
