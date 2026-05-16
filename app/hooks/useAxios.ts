"use client";
import { useRef, useState, useCallback } from "react";
import type { AxiosRequestConfig, AxiosResponse } from "axios";
import { http } from "../services/axios";
import { endpoints, type endpointsType, type endpointType } from "../services/endpoints";
import { App } from "antd";
import { AUTH_COOKIE_KEY } from "../config/config";
import { deleteCookie, setCookie } from "../config/cookies";
import { useRouter } from "next/navigation";

export interface axiosConfig<R> extends AxiosRequestConfig<R> {
  path?: string;
  data?: R;
  showLoader?: boolean;
  isFormData?: boolean; // ✅ added
}

const DEFAULT_SUCCESS_STATUS_CODES = [200, 201];

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
  skipAuthRedirect?: boolean;
}) {
  const {
    endpoint,
    showSuccessMsg = false,
    hideErrorMsg = false,
    successMsg = "",
    initialData,
    initialLoading = false,
    successStatusCode = DEFAULT_SUCCESS_STATUS_CODES,
    payload,
    successCb,
    skipAuthRedirect = false,
  } = opts || {};

  const router = useRouter();
  const [loading, setLoading] = useState(initialLoading);
  const [data, setData] = useState<T>(initialData as T);
  const controller = useRef<AbortController | null>(null);
  const { notification } = App.useApp();

  const { url, method, baseURL, withCredentials } = (
    endpoint ? (endpoints[endpoint] as endpointType) : {}
  ) as endpointType;

  const request = useCallback(async (config?: axiosConfig<R>, cb?: (resData: T) => void) => {
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
        let msg = successMsg;
        if (typeof res.data === "object" && res.data !== null) {
          const d = res.data as Record<string, any>;
          if (typeof d.message === "string") {
            msg = msg || d.message;
          } else if (d.meta && typeof d.meta.message === "string") {
            msg = msg || d.meta.message;
          }
        }
        
        if (showSuccessMsg || msg) {
          notification.success({ title: "Success", description: msg || "Success", showProgress: true, pauseOnHover: true, className: "custom-toast-success" });
        }
      } else {
        if (!hideErrorMsg) {
          let msg = "Internal error";
          if (typeof res.data === "object" && res.data !== null) {
            const d = res.data as Record<string, any>;
            if (typeof d.message === "string") {
              msg = d.message;
            } else if (d.meta && typeof d.meta.message === "string") {
              msg = d.meta.message;
            }
          }
          notification.error({ title: "Error", description: msg, showProgress: true, pauseOnHover: true, className: "custom-toast-error" });
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

      if (err?.response?.status === 401 && !skipAuthRedirect) {
        deleteCookie(AUTH_COOKIE_KEY);
        notification.warning({
          title: "Session Expired",
          description: "Please login again, your session has expired.",
          showProgress: true,
          pauseOnHover: true,
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
          const d = err.response.data as Record<string, any>;
          if (typeof d.message === "string") msg = d.message;
          else if (d.meta && typeof d.meta.message === "string") msg = d.meta.message;
          else if (typeof d.title === "string") msg = d.title;
        } else if (err?.message) {
          msg = err.message;
        }
        notification.error({ title: "Error", description: msg, showProgress: true, pauseOnHover: true, className: "custom-toast-error" });
      }
    }

    setLoading(false);
  }, [baseURL, endpoint, hideErrorMsg, initialData, method, notification, payload, router, showSuccessMsg, successCb, successMsg, successStatusCode, url, withCredentials]);

  return [request, data, loading, setData, setLoading] as const;
}