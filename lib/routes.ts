export const routes = {
  login: "/auth/login",
  register: "/auth/register",
  dashboard: "/dashboard",
} as const;

export type RouteKey = keyof typeof routes;

export function getRoute(key: RouteKey) {
  return routes[key];
}
