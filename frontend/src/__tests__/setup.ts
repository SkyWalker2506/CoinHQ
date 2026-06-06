import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach } from "vitest";

/**
 * Defensive localStorage shim.
 *
 * jsdom (the vitest environment) provides `window.localStorage` natively, but
 * earlier versions had bugs where `localStorage.clear` could be undefined in
 * specific test setups (see Run 3 forge lessons). This shim guarantees the
 * full Storage API is always present so per-test cleanup never throws.
 *
 * It also resets the storage between tests so suites don't bleed state into
 * each other (logout test setting `token` would otherwise leak).
 */
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length() {
    return this.store.size;
  }
  clear(): void {
    this.store.clear();
  }
  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }
  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

function ensureStorage(slot: "localStorage" | "sessionStorage"): void {
  const existing = (globalThis as unknown as Record<string, unknown>)[slot] as
    | Storage
    | undefined;
  // Replace if missing OR if any required method is absent (older jsdom).
  const incomplete =
    !existing ||
    typeof existing.clear !== "function" ||
    typeof existing.getItem !== "function" ||
    typeof existing.setItem !== "function" ||
    typeof existing.removeItem !== "function";
  if (incomplete) {
    Object.defineProperty(globalThis, slot, {
      value: new MemoryStorage(),
      writable: true,
      configurable: true,
    });
  }
}

ensureStorage("localStorage");
ensureStorage("sessionStorage");

beforeEach(() => {
  // Guard against suites that mutate storage without restoring it.
  globalThis.localStorage?.clear?.();
  globalThis.sessionStorage?.clear?.();
});

afterEach(() => {
  globalThis.localStorage?.clear?.();
  globalThis.sessionStorage?.clear?.();
});
