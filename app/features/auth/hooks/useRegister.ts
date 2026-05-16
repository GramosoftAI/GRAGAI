"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setCookie } from "../../../config/cookies";
import { AUTH_COOKIE_KEY } from "../../../config/config";
import { routes } from "../../../services/routes";
import { useStore } from "../../../hooks/useStore";
import { useRegisterApi } from "../api";
import { RegisterFormValues } from "../types";

export function useRegister() {
  const router = useRouter();
  const [request] = useRegisterApi();
  const setUserId = useStore((s) => s.setUserId);

  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function register(values: RegisterFormValues) {
    setError(null);
    setIsSubmitting(true);

    try {
      await request(
        {
          data: {
            first_name: values.first_name.trim(),
            last_name: values.last_name.trim(),
            email: values.email.trim(),
            password: values.password,
            confirm_password: values.confirm_password,
            tenant_name: values.tenant_name.trim(),
          },
        },
        (res: any) => {
          const responseData = res?.data;
          const user = responseData?.user;
          const userId = user?.id;

          if (userId) setUserId(userId);

          if (user) {
            localStorage.setItem("userName", `${user.first_name} ${user.last_name}`);
          }

          const token = responseData?.tokens?.access_token ?? "";
          setCookie(AUTH_COOKIE_KEY, token);
        }
      );

      router.push(routes.dashboard);
    } catch (err: unknown) {
      let msg = "Registration failed";
      if (typeof err === "object" && err && "data" in err) {
        const d = (err as { data?: unknown }).data;
        if (d && typeof d === "object" && "message" in d) {
          const m = (d as { message?: unknown }).message;
          if (typeof m === "string") msg = m;
        }
      }
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  }

  return { register, error, isSubmitting };
}