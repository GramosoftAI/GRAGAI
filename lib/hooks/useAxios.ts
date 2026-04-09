import { useRef, useState } from "react";
import type { AxiosRequestConfig, AxiosResponse } from "axios";
import { http } from "@/lib/http/axios";
import { endpoints, type endpointsType, type endpointType } from "@/lib/http/endpoints";
import { toast } from "sonner";
import { AUTH_COOKIE_KEY } from "@/lib/config";
import { deleteCookie, setCookie } from "@/lib/cookies";
import { useRouter } from "next/navigation";

export interface axiosConfig<R> extends AxiosRequestConfig<R> {
  path?: string;
  data?: R;
  showLoader?: boolean;
  isFormData?: boolean; // ✅ added
}

export default function useAxios<T = unknown, R = unknown>(opts?: {
  endpoint?: endpointsType;
  showSuccessMsg?: boolean;
  hideErrorMsg?: boolean;
  successMsg?: string;
  initialData?: T;
  initialLoading?: boolean;
  successStatusCode?: number[];
  payload?: R;
  successCb?: () => void;
}) {
  const {
    endpoint,
    showSuccessMsg = false,
    hideErrorMsg = false,
    successMsg = "",
    initialData,
    initialLoading = false,
    successStatusCode = [200, 201],
    payload,
    successCb,
  } = opts || {};

  const router = useRouter();
  const [loading, setLoading] = useState(initialLoading);
  const [data, setData] = useState<T>(initialData as T);
  const controller = useRef<AbortController | null>(null);

  const { url, method, baseURL, withCredentials } = (
    endpoint ? (endpoints[endpoint] as endpointType) : {}
  ) as endpointType;

  const request = async (config?: axiosConfig<R>, cb?: (resData: T) => void) => {
    try {
      controller.current?.abort();
      setLoading(true);
      controller.current = new AbortController();

      // ✅ if isFormData, let browser set Content-Type with boundary automatically
      //    if JSON, explicitly set Content-Type: application/json
      const headers = config?.isFormData
        ? { ...(config?.headers ?? {}) }
        : { "Content-Type": "application/json", ...(config?.headers ?? {}) };

const res: AxiosResponse<T> = await http.request<T, AxiosResponse<T>, R>({
  method,
  baseURL,
  withCredentials,
  url: (url || "") + (config?.path ?? ""),
  signal: controller.current.signal,
  data: (config?.data as R) ?? (payload as R),
  timeout: 60000,
  ...config,
  headers, // ✅ spread config first, then override headers so it always wins
});

      const tokenHeaderRaw = (res.headers as Record<string, string | string[] | undefined>)["x-token"];
      const tokenHeader = Array.isArray(tokenHeaderRaw) ? tokenHeaderRaw[0] : tokenHeaderRaw;
      const isFirstTime =
        typeof res.data === "object" && res.data !== null && "isFirstTime" in res.data
          ? (res.data as Record<string, unknown>).isFirstTime === false
          : false;
      if (tokenHeader && isFirstTime === false) {
        setCookie(AUTH_COOKIE_KEY, tokenHeader);
      }

      const statusOk = successStatusCode.includes(res.status);
      const resStatus =
        typeof res.data === "object" && res.data !== null && "status" in res.data
          ? (res.data as Record<string, unknown>).status
          : undefined;

      if (statusOk && resStatus !== false) {
        successCb?.();
        (cb ? cb : setData)(res?.data ?? (null as unknown as T));
        if (showSuccessMsg) {
          let msg = successMsg || "Success";
          if (typeof res.data === "object" && res.data !== null) {
            if (
              "message" in res.data &&
              typeof (res.data as Record<string, unknown>).message === "string"
            ) {
              msg = (res.data as Record<string, unknown>).message as string;
            }
          }
          toast.success(msg, { duration: 4000 });
        }
      } else {
        if (!hideErrorMsg) {
          const msg =
            typeof res.data === "object" &&
            res.data !== null &&
            "message" in res.data &&
            typeof (res.data as Record<string, unknown>).message === "string"
              ? ((res.data as Record<string, unknown>).message as string)
              : "Internal error";
          toast.error(msg, { duration: 5000 });
        }
      }

      setLoading(false);
      return res.data as T;
    } catch (error: unknown) {
      setData(initialData as T);
      const err = error as {
        response?: { status?: number; data?: unknown };
        code?: string;
        message?: string;
      };

      if (err?.response?.status === 401) {
        deleteCookie(AUTH_COOKIE_KEY);
        toast.warning("Session Expired: Please login again, your session has expired.", {
          duration: 6000,
        });
        router.push("/login");
        setLoading(false);
        return;
      }

      if (
        !["ERR_CANCELED", "ECONNABORTED"].includes(err?.code ?? "") &&
        !hideErrorMsg
      ) {
        let msg = "Something went wrong";
        if (typeof err?.response?.data === "string") msg = err.response.data;
        else if (err?.response?.data && typeof err.response.data === "object") {
          const d = err.response.data as Record<string, unknown>;
          if (typeof d.message === "string") msg = d.message;
          else if (typeof d.title === "string") msg = d.title;
        } else if (err?.message) {
          msg = err.message;
        }
        toast.error(msg, { duration: 6000 });
      }
    }

    setLoading(false);
  };

  return [request, data, loading, setData, setLoading] as const;
}