"use client";

import { GitHubUserProfile, GitHubTokenPermissions } from "@/types";

const TOKEN_KEY = "devsquad_github_token";
const USERNAME_KEY = "devsquad_github_username";
const PROFILE_KEY = "devsquad_github_profile";
const PERMISSIONS_KEY = "devsquad_github_permissions";

export function getStoredGitHubToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredGitHubUsername(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(USERNAME_KEY);
}

export function getStoredGitHubPermissions(): GitHubTokenPermissions | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PERMISSIONS_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function getStoredGitHubProfile(): GitHubUserProfile | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PROFILE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setStoredGitHubSession(
  token?: string | null,
  username?: string | null,
  profile?: GitHubUserProfile | null,
  permissions?: GitHubTokenPermissions | null
): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else if (token === null) {
    localStorage.removeItem(TOKEN_KEY);
  }

  if (username) {
    localStorage.setItem(USERNAME_KEY, username);
  } else if (username === null) {
    localStorage.removeItem(USERNAME_KEY);
  }

  if (profile) {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  } else if (profile === null) {
    localStorage.removeItem(PROFILE_KEY);
  }

  if (permissions) {
    localStorage.setItem(PERMISSIONS_KEY, JSON.stringify(permissions));
  } else if (permissions === null) {
    localStorage.removeItem(PERMISSIONS_KEY);
  }

  // Dispatch custom storage event for in-tab reactive updates
  window.dispatchEvent(new Event("devsquad_github_session_change"));
}

export function clearStoredGitHubSession(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
  localStorage.removeItem(PROFILE_KEY);
  localStorage.removeItem(PERMISSIONS_KEY);
  window.dispatchEvent(new Event("devsquad_github_session_change"));
}
