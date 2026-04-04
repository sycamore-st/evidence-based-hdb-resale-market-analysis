import { readFile } from "node:fs/promises"
import path from "node:path"

const REPO_ROOT = path.resolve(process.cwd(), "../..")
const SECTION1_DATA_BASE_URL = process.env.SECTION1_DATA_BASE_URL?.replace(/\/+$/, "")

function toLocalPath(relativePath: string): string {
  return path.join(REPO_ROOT, relativePath)
}

function toRemoteUrl(relativePath: string): string {
  if (!SECTION1_DATA_BASE_URL) {
    throw new Error("SECTION1_DATA_BASE_URL is not configured")
  }
  return `${SECTION1_DATA_BASE_URL}/${relativePath.replace(/^\/+/, "")}`
}

export function isRemoteSection1DataEnabled(): boolean {
  return Boolean(SECTION1_DATA_BASE_URL)
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
