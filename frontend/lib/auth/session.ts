/**
 * Session and token management for DevSquad Maintainer.
 * Uses localStorage with sessionStorage and in-memory fallback.
 */

import { User } from "@/types";

let inMemoryToken: string | null = null;
let inMemoryUser: User | null = null;

const TOKEN_KEY = "devsquad_session_token";
const USER_KEY = "devsquad_session_user";

export function getSessionToken(): string | null {
  if (inMemoryToken) return inMemoryToken;
  if (typeof window !== "undefined") {
    inMemoryToken =
      localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
  }
  return inMemoryToken;
}

export function getSessionUser(): User | null {
  if (inMemoryUser) return inMemoryUser;
  if (typeof window !== "undefined") {
    const raw =
      localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
    if (raw) {
      try {
        inMemoryUser = JSON.parse(raw);
      } catch {
        inMemoryUser = null;
      }
    }
  }
  return inMemoryUser;
}

export function setSession(token: string, user: User): void {
  inMemoryToken = token;
  inMemoryUser = user;
  if (typeof window !== "undefined") {
    try {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      // ignore storage quota issues
    }
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
      sessionStorage.setItem(USER_KEY, JSON.stringify(user));
    } catch {
      // ignore storage quota issues
    }
  }
}

export function clearSession(): void {
  inMemoryToken = null;
  inMemoryUser = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }
}

export function isAuthenticated(): boolean {
  return !!getSessionToken();
}
