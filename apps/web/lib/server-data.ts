import { readFile } from "node:fs/promises"
import path from "node:path"

const REPO_ROOT = path.resolve(process.cwd(), "../..")
const SECTION1_DATA_BASE_URL = process.env.SECTION1_DATA_BASE_URL?.replace(/\/+$/, "")
const GITHUB_REPO_BASE = "https://github.com/sycamore-st/evidence-based-hdb-resale-market-analysis/blob/production"
const GITHUB_RAW_BASE = "https://raw.githubusercontent.com/sycamore-st/evidence-based-hdb-resale-market-analysis/production"

function toLocalPath(relativePath: string): string {
  return path.join(REPO_ROOT, relativePath)
}

function toRemoteUrl(relativePath: string): string {
  if (!SECTION1_DATA_BASE_URL) {
    throw new Error("SECTION1_DATA_BASE_URL is not configured")
  }
  return `${SECTION1_DATA_BASE_URL}/${relativePath.replace(/^\/+/, "")}`
}

function sanitizeRepoPath(relativePath: string): string {
  return relativePath.replace(/^\/+/, "")
}

export function isRemoteSection1DataEnabled(): boolean {
  return Boolean(SECTION1_DATA_BASE_URL)
}

export function resolveRepositoryBlobUrl(relativePath: string): string {
  return `${GITHUB_REPO_BASE}/${sanitizeRepoPath(relativePath)}`
}

export function resolveRepositoryRawUrl(relativePath: string): string {
  return `${GITHUB_RAW_BASE}/${sanitizeRepoPath(relativePath)}`
}

export function resolvePublicAssetUrl(relativePath: string): string {
  const normalizedPath = sanitizeRepoPath(relativePath)

  if (SECTION1_DATA_BASE_URL && (normalizedPath.startsWith("outputs/section1/") || normalizedPath.startsWith("artifacts/web/"))) {
    return toRemoteUrl(normalizedPath)
  }

  if (normalizedPath.startsWith("outputs/") || normalizedPath.startsWith("docs/")) {
    return resolveRepositoryRawUrl(normalizedPath)
  }

  return resolveRepositoryBlobUrl(normalizedPath)
}

export async function readTextAsset(relativePath: string): Promise<string> {
  if (!SECTION1_DATA_BASE_URL) {
    return readFile(toLocalPath(relativePath), "utf8")
  }

  const response = await fetch(toRemoteUrl(relativePath), {
    cache: "no-store",
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch ${relativePath} from remote storage: ${response.status} ${response.statusText}`)
  }

  return response.text()
}

export async function readJsonAsset<T>(relativePath: string): Promise<T> {
  return JSON.parse(await readTextAsset(relativePath)) as T
}
