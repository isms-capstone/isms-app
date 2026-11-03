import { api } from "./api";
import type { BackendContract } from "./worklog-contract";

export function backendCapabilities(signal?: AbortSignal) {
  return api<BackendContract>("/capabilities", { signal });
}
