import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  const pathname = req.nextUrl.pathname;
  if (pathname.startsWith("/_next") || pathname.startsWith("/api") || pathname.startsWith("/favicon")) {
    return NextResponse.next();
  }
  const publicRoutes = ["/home","/auth/login", "/auth/register"];
  if (publicRoutes.includes(pathname)) {
    return NextResponse.next();
  }
  const key = process.env.AUTH_COOKIE_KEY || "AUTH_TOKEN";
  const token = req.cookies.get(key)?.value;
//   Commenting out the redirect to allow "login without access" (direct access)
  if (!token) {
    const url = req.nextUrl.clone();
    url.pathname = "/home";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};