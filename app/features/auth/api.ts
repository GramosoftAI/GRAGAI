import useAxios from "@/app/hooks/useAxios";
import { LoginPayload, LoginResponse, RegisterPayload, RegisterResponse } from "./types";
import { log } from "console";

// ─── Login ────────────────────────────────────────────────────────────────────

export function useLoginApi() {
  return useAxios<LoginResponse, LoginPayload>({
    endpoint: "LOGIN",
    hideErrorMsg: false,
  });

}


// ─── Register ─────────────────────────────────────────────────────────────────

export function useRegisterApi() {
  return useAxios<RegisterResponse, RegisterPayload>({
    endpoint: "REGISTER",
    hideErrorMsg: false,
  });
}