// "use client";
// import { useRef, useState, useCallback } from "react";
// import type { AxiosRequestConfig, AxiosResponse } from "axios";
// import { http } from "../services/axios";
// import { endpoints, type endpointsType, type endpointType } from "../services/endpoints";
// import { App } from "antd";
// import { AUTH_COOKIE_KEY } from "../config/config";
// import { deleteCookie, setCookie } from "../config/cookies";
// import { useRouter } from "next/navigation";

// export interface axiosConfig<R> extends AxiosRequestConfig<R> {
//   path?: string;
//   data?: R;
//   showLoader?: boolean;
//   isFormData?: boolean; // ✅ added
// }

// const DEFAULT_SUCCESS_STATUS_CODES = [200, 201];

// export default function useAxios<T = unknown, R = unknown>(opts?: {
//   endpoint?: endpointsType;
//   showSuccessMsg?: boolean;
//   hideErrorMsg?: boolean;
//   successMsg?: string;
//   initialData?: T;
//   initialLoading?: boolean;
//   successStatusCode?: number[];
//   payload?: R;
//   successCb?: () => void;
//   skipAuthRedirect?: boolean;
// }) {
//   const {
//     endpoint,
//     showSuccessMsg = false,
//     hideErrorMsg = false,
//     successMsg = "",
//     initialData,
//     initialLoading = false,
//     successStatusCode = DEFAULT_SUCCESS_STATUS_CODES,
//     payload,
//     successCb,
//     skipAuthRedirect = false,
//   } = opts || {};

//   const router = useRouter();
//   const [loading, setLoading] = useState(initialLoading);
//   const [data, setData] = useState<T>(initialData as T);
//   const controller = useRef<AbortController | null>(null);
//   const { notification } = App.useApp();

//   const { url, method, baseURL, withCredentials } = (
//     endpoint ? (endpoints[endpoint] as endpointType) : {}
//   ) as endpointType;

//   const request = useCallback(async (config?: axiosConfig<R>, cb?: (resData: T) => void) => {
//     try {
//       controller.current?.abort();
//       setLoading(true);
//       controller.current = new AbortController();

//       // ✅ if isFormData, let browser set Content-Type with boundary automatically
//       //    if JSON, explicitly set Content-Type: application/json
//       const headers = config?.isFormData
//         ? { ...(config?.headers ?? {}) }
//         : { "Content-Type": "application/json", ...(config?.headers ?? {}) };

// const res: AxiosResponse<T> = await http.request<T, AxiosResponse<T>, R>({
//   method,
//   baseURL,
//   withCredentials,
//   url: (url || "") + (config?.path ?? ""),
//   signal: controller.current.signal,
//   data: (config?.data as R) ?? (payload as R),
//   timeout: 6000000,
//   ...config,
//   headers, // ✅ spread config first, then override headers so it always wins
// });

//       const tokenHeaderRaw = (res.headers as Record<string, string | string[] | undefined>)["x-token"];
//       const tokenHeader = Array.isArray(tokenHeaderRaw) ? tokenHeaderRaw[0] : tokenHeaderRaw;
//       const isFirstTime =
//         typeof res.data === "object" && res.data !== null && "isFirstTime" in res.data
//           ? (res.data as Record<string, unknown>).isFirstTime === false
//           : false;
//       if (tokenHeader && isFirstTime === false) {
//         setCookie(AUTH_COOKIE_KEY, tokenHeader);
//       }

//       const statusOk = successStatusCode.includes(res.status);
//       const resStatus =
//         typeof res.data === "object" && res.data !== null && "status" in res.data
//           ? (res.data as Record<string, unknown>).status
//           : undefined;

//       if (statusOk && resStatus !== false) {
//         successCb?.();
//         (cb ? cb : setData)(res?.data ?? (null as unknown as T));
//         let msg = successMsg;
//         if (typeof res.data === "object" && res.data !== null) {
//           const d = res.data as Record<string, any>;
//           if (typeof d.message === "string") {
//             msg = msg || d.message;
//           } else if (d.meta && typeof d.meta.message === "string") {
//             msg = msg || d.meta.message;
//           }
//         }
        
//         if (showSuccessMsg || msg) {
//           notification.success({ title: "Success", description: msg || "Success", showProgress: true, pauseOnHover: true, className: "custom-toast-success" });
//         }
//       } else {
//         if (!hideErrorMsg) {
//           let msg = "Internal error";
//           if (typeof res.data === "object" && res.data !== null) {
//             const d = res.data as Record<string, any>;
//             if (typeof d.message === "string") {
//               msg = d.message;
//             } else if (d.meta && typeof d.meta.message === "string") {
//               msg = d.meta.message;
//             }
//           }
//           notification.error({ title: "Error", description: msg, showProgress: true, pauseOnHover: true, className: "custom-toast-error" });
//         }
//       }

//       setLoading(false);
//       return res.data as T;
//     } catch (error: unknown) {
//       setData(initialData as T);
//       const err = error as {
//         response?: { status?: number; data?: unknown };
//         code?: string;
//         message?: string;
//       };

//       if (err?.response?.status === 401 && !skipAuthRedirect) {
//         deleteCookie(AUTH_COOKIE_KEY);
//         notification.warning({
//           // title: "Session Expired",
//           description: "Please login again.",
//           showProgress: true,
//           pauseOnHover: true,
//         });
//         router.push("/login");
//         setLoading(false);
//         return;
//       }

//       if (
//         !["ERR_CANCELED", "ECONNABORTED"].includes(err?.code ?? "") &&
//         !hideErrorMsg
//       ) {
//         let msg = "Something went wrong";
//         if (typeof err?.response?.data === "string") msg = err.response.data;
//         else if (err?.response?.data && typeof err.response.data === "object") {
//           const d = err.response.data as Record<string, any>;
//           if (typeof d.message === "string") msg = d.message;
//           else if (d.meta && typeof d.meta.message === "string") msg = d.meta.message;
//           else if (typeof d.title === "string") msg = d.title;
//         } else if (err?.message) {
//           msg = err.message;
//         }
//         notification.error({ title: "Error", description: msg, showProgress: true, pauseOnHover: true, className: "custom-toast-error" });
//       }
//     }

//     setLoading(false);
//   }, [baseURL, endpoint, hideErrorMsg, initialData, method, notification, payload, router, showSuccessMsg, successCb, successMsg, successStatusCode, url, withCredentials]);

//   return [request, data, loading, setData, setLoading] as const;
// }



// /* eslint-disable @typescript-eslint/no-explicit-any */

import axios from "axios";
import type {
  AxiosRequestConfig,
  AxiosResponse,
  Method,
} from "axios";

import { useRef, useState , useCallback} from "react";
// import { App as AntApp } from "antd";
// import Cookies from "js-cookie";
import { getCookie } from "../config/cookies";
import { toast } from "react-hot-toast";
import {useRouter} from "next/navigation"
import { endpoints, type endpointsType, type endpointType } from "../services/endpoints";
// import { endpoints } from "./endpoints";
// import type { endpointType, endpointsType } from "./endpoints";

const DEFAULT_SUCCESS_STATUS_CODES = [200, 201];

/* -------------------------------------------------------------------------- */
/*                                AXIOS SETUP                                 */
/* -------------------------------------------------------------------------- */

axios.defaults.baseURL = process.env.NEXT_PUBLIC_API_BASE_URL;

/* -------------------------------------------------------------------------- */
/*                                   TYPES                                    */
/* -------------------------------------------------------------------------- */

export interface AxiosConfig<R> extends AxiosRequestConfig {
  path?: string;
  data?: R;
  isFormData?: boolean;
}

interface UseAxiosProps<T, R> {
  endpoint?: endpointsType;

  showSuccessMsg?: boolean;
  hideErrorMsg?: boolean;

  successMsg?: string;

  initialData?: T;
  initialLoading?: boolean;

  successStatusCode?: number[];

  payload?: R;

  successCb?: () => void;
  errorCb?: () => void;
}

/* -------------------------------------------------------------------------- */
/*                                CUSTOM HOOK                                 */
/* -------------------------------------------------------------------------- */

export default function useAxios<T = any, R = any>({
  endpoint,

  showSuccessMsg = false,
  hideErrorMsg = false,

  successMsg = "",

  initialData,
  initialLoading = false,

  successStatusCode = DEFAULT_SUCCESS_STATUS_CODES,

  payload,

  successCb,
  errorCb,
}: UseAxiosProps<T, R>) {
  // const { message } = AntApp.useApp();

  /* -------------------------------------------------------------------------- */
  /*                               ENDPOINT DATA                                */
  /* -------------------------------------------------------------------------- */

  const {
    url = "",
    method = "GET",
    baseURL,
    withCredentials,
  } = endpoint
    ? (endpoints[endpoint] as endpointType)
    : {};

  /* -------------------------------------------------------------------------- */
  /*                                   STATES                                   */
  /* -------------------------------------------------------------------------- */

  const [loading, setLoading] = useState(initialLoading);
  const router = useRouter();
  const [data, setData] = useState<T>(initialData as T);

  /* -------------------------------------------------------------------------- */
  /*                             ABORT CONTROLLER                               */
  /* -------------------------------------------------------------------------- */

  const controller = useRef<AbortController | null>(null);

  /* -------------------------------------------------------------------------- */
  /*                                MAIN REQUEST                                */
  /* -------------------------------------------------------------------------- */

  

  const request =useCallback( async (
    config?: AxiosConfig<R>,
    cb?: (resData: T) => void
  ) => {
    try {
      /* -------------------------------------------------------------------------- */
      /*                          CANCEL PREVIOUS REQUEST                            */
      /* -------------------------------------------------------------------------- */

      controller.current?.abort();

      controller.current = new AbortController();

      setLoading(true);


      const token = getCookie("AUTH_TOKEN");

      /* -------------------------------------------------------------------------- */
      /*                                  HEADERS                                   */
      /* -------------------------------------------------------------------------- */

      const headers = config?.isFormData
        ? {
            ...(config?.headers ?? {}),
            Authorization: token ? `Bearer ${token}` : "",
          }
        : {
            "Content-Type": "application/json",

            Authorization: token ? `Bearer ${token}` : "",

            ...(config?.headers ?? {}),
          };

      /* -------------------------------------------------------------------------- */
      /*                               AXIOS REQUEST                                */
      /* -------------------------------------------------------------------------- */

      const response: AxiosResponse<any> =
        await axios.request({
          method: method as Method,

          baseURL,

          withCredentials,

          url: url + (config?.path ?? ""),

          signal: controller.current.signal,

          timeout: 5 * 60000,

          headers,

          data: config?.data ?? payload,

          ...config,
        });

     
      /* -------------------------------------------------------------------------- */
      /*                              SUCCESS HANDLING                              */
      /* -------------------------------------------------------------------------- */

      const isSuccess =
        // response.status === successStatusCode 
       successStatusCode.includes(response.status) &&
        (response.data?.status ??
          response.data?.result?.status) !== false;

      if (isSuccess) {
        successCb?.();

        const responseData =
          response?.data || null;

        if (cb) {
          cb(responseData);
        } else {
          setData(responseData);
        }

        if (showSuccessMsg) {
          toast.success(
            response?.data?.message ??
              response?.data?.result?.message ?? response?.data?.meta?.message ??
              successMsg
          );
        }

        return responseData as T;
      }

      /* -------------------------------------------------------------------------- */
      /*                               FAILED RESPONSE                              */
      /* -------------------------------------------------------------------------- */

      if (!hideErrorMsg) {
        if(response.status === 201)
        {
          toast.success(
            response?.data?.message ??
              response?.data?.result?.message ?? response?.data?.meta?.message ??
              successMsg
          );
        }
        else{
          toast.error(
            response?.data?.message || response?.data?.detail || response?.data?.meta?.message ||
              "Something went wrong"
          );
        }
      }

      errorCb?.();

      return null;
    } catch (error: any) {
      /* -------------------------------------------------------------------------- */
      /*                              RESET DATA STATE                              */
      /* -------------------------------------------------------------------------- */

      setData(initialData as T);
      console.log("Full Error:", error);
  console.log("Status:", error?.response?.status);
  console.log("Data:", error?.response?.data);

      if (error.response?.status === 401) {
    toast.error(
      error?.response?.data?.detail ||
      error?.response?.data?.message || error?.response?.data?.error || error?.response?.data?.meta?.message ||
      "Invalid username or password"
    );
    router.push("/login");
    return null;
  }

  // toast.error(
  //   error?.response?.data?.detail ||
  //   error?.response?.data?.message ||
  //   error?.response?.data?.title ||
  //   error?.message ||
  //   "Something went wrong"
  // );


      if (error.code === "ERR_CANCELED") {
        return;
      }

      /* -------------------------------------------------------------------------- */
      /*                              NORMAL ERRORS                                 */
      /* -------------------------------------------------------------------------- */

      if (
        !["ERR_CANCELED", "ECONNABORTED"].includes(
          error.code
        ) &&
        !hideErrorMsg
      ) {
        toast.error(
          (typeof error?.response?.data ===
          "string"
            ? error?.response?.data
            : error?.response?.data?.message) ||
            error?.response?.data?.title ||
            error?.message ||
            "Something went wrong"
        );
      // router.push("/login");
      }

      errorCb?.();

      return null;
    } finally {
      /* -------------------------------------------------------------------------- */
      /*                              STOP LOADING                                  */
      /* -------------------------------------------------------------------------- */

      setLoading(false);
    }
    }, [baseURL, hideErrorMsg, initialData, method, payload, router, showSuccessMsg, successCb, errorCb, successMsg, successStatusCode, url, withCredentials]);

  /* -------------------------------------------------------------------------- */
  /*                                   RETURN                                   */
  /* -------------------------------------------------------------------------- */

  return [
    request,
    data,
    loading,
    setData,
    setLoading,
  ] as const;
}