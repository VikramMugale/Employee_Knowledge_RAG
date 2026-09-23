export function fetchOAuthStatus() {
  return fetch("/api/v1/auth/oauth/status").then(async (response) => {
    if (!response.ok) throw new Error("Could not load OAuth status");
    return response.json();
  });
}
