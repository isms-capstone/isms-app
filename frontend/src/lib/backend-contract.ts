import {
  inspectBackendContract,
  type BackendContract,
} from "./worklog-contract";

let cached:
  | { url: string; expires: number; contract: Promise<BackendContract> }
  | undefined;

export function backendContract(url: string): Promise<BackendContract> {
  if (cached?.url === url && cached.expires > Date.now())
    return cached.contract;
  const contract = fetch(`${url}/openapi.json`, {
    cache: "no-store",
    signal: AbortSignal.timeout(10000),
    redirect: "error",
  })
    .then(async (response) => {
      if (!response.ok) throw new Error("Cannot inspect backend API contract");
      return inspectBackendContract(await response.json());
    })
    .catch((error) => {
      if (cached?.contract === contract) cached = undefined;
      throw error;
    });
  cached = { url, expires: Date.now() + 30000, contract };
  return contract;
}
