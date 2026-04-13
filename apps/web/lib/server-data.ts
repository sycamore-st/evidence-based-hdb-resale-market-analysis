import { readFile } from "node:fs/promises"
import path from "node:path"

const REPO_ROOT = path.resolve(process.cwd(), "../..")
const ASSET_BASE_URL = (
  process.env.ASSET_BASE_URL ??
  process.env.NEXT_PUBLIC_ASSET_BASE_URL ??
  process.env.SECTION1_DATA_BASE_URL
) ?.replace(/\/+$/, "")
const ASSET_VERSION = (
  process.env.NEXT_PUBLIC_ASSET_VERSION ??
  process.env.NEXT_PUBLIC_VERCEL_GIT_COMMIT_SHA ??
  process.env.ASSET_VERSION ??
  process.env.VERCEL_GIT_COMMIT_SHA
) ?.trim()
const GITHUB_REPO_BASE = "https://github.com/sycamore-st/evidence-based-hdb-resale-market-analysis/blob/production"
const GITHUB_RAW_BASE = "https://raw.githubusercontent.com/sycamore-st/evidence-based-hdb-resale-market-analysis/production"

function toLocalPath(relativePath: string): string {
  return path.join(REPO_ROOT, relativePath)
}

function toSubmissionFallbackPath(relativePath: string): string | null {
  const normalizedPath = sanitizeRepoPath(relativePath)

  if (!normalizedPath.startsWith("outputs/")) {
    return null
  }

  return path.join(REPO_ROOT, normalizedPath.replace(/^outputs\//, "outputs_submission/"))
}

function toRemoteUrl(relativePath: string): string {
  if (!ASSET_BASE_URL) {
    throw new Error("ASSET_BASE_URL is not configured")
  }
  const base = `${ASSET_BASE_URL}/${relativePath.replace(/^\/+/, "")}`
  return appendAssetVersion(base)
}

function sanitizeRepoPath(relativePath: string): string {
  return relativePath.replace(/^\/+/, "")
}

function appendAssetVersion(url: string): string {
  if (!ASSET_VERSION) {
    return url
  }

  try {
    const parsed = new URL(url)
    if (!parsed.searchParams.has("assetv")) {
      parsed.searchParams.set("assetv", ASSET_VERSION)
    }
    return parsed.toString()
  } catch {
    if (url.includes("assetv=")) {
      return url
    }
    const separator = url.includes("?") ? "&" : "?"
    return `${url}${separator}assetv=${encodeURIComponent(ASSET_VERSION)}`
  }
}

export function isRemoteSection1DataEnabled(): boolean {
  return Boolean(ASSET_BASE_URL)
}

export function resolveRepositoryBlobUrl(relativePath: string): string {
  return `${GITHUB_REPO_BASE}/${sanitizeRepoPath(relativePath)}`
}

export function resolveRepositoryRawUrl(relativePath: string): string {
  return `${GITHUB_RAW_BASE}/${sanitizeRepoPath(relativePath)}`
}

export function resolvePublicAssetUrl(relativePath: string): string {
  const normalizedPath = sanitizeRepoPath(relativePath)

  if (ASSET_BASE_URL && (normalizedPath.startsWith("outputs/") || normalizedPath.startsWith("artifacts/"))) {
    return toRemoteUrl(normalizedPath)
  }

  if (
    normalizedPath.startsWith("outputs/") ||
    normalizedPath.startsWith("artifacts/") ||
    normalizedPath.startsWith("docs/")
  ) {
    if (normalizedPath.startsWith("outputs/") || normalizedPath.startsWith("artifacts/")) {
      return appendAssetVersion(`/${normalizedPath}`)
    }
    return `/${normalizedPath}`
  }

  return resolveRepositoryBlobUrl(normalizedPath)
}

export async function readTextAsset(relativePath: string): Promise<string> {
  const normalizedPath = sanitizeRepoPath(relativePath)

  if (!ASSET_BASE_URL || (!normalizedPath.startsWith("outputs/") && !normalizedPath.startsWith("artifacts/"))) {
    try {
      return await readFile(toLocalPath(relativePath), "utf8")
    } catch (error) {
      const fallbackPath = toSubmissionFallbackPath(relativePath)

      if ((error as NodeJS.ErrnoException).code !== "ENOENT" || !fallbackPath) {
        throw error
      }

      return readFile(fallbackPath, "utf8")
    }
  }

  const response = await fetch(toRemoteUrl(normalizedPath), {
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
