const GITHUB_REPO_BASE = "https://github.com/sycamore-st/evidence-based-hdb-resale-market-analysis/blob/production"
const ASSET_BASE_URL = (
  process.env.NEXT_PUBLIC_ASSET_BASE_URL ??
  process.env.ASSET_BASE_URL ??
  process.env.SECTION1_DATA_BASE_URL
) ?.replace(/\/+$/, "")

function sanitizeRepoPath(relativePath: string): string {
  return relativePath.replace(/^\/+/, "")
}

function resolveRepositoryBlobUrl(relativePath: string): string {
  return `${GITHUB_REPO_BASE}/${sanitizeRepoPath(relativePath)}`
}

function resolvePublicAssetUrl(relativePath: string): string {
  const normalizedPath = sanitizeRepoPath(relativePath)

  if (ASSET_BASE_URL && (normalizedPath.startsWith("outputs/") || normalizedPath.startsWith("artifacts/"))) {
    return `${ASSET_BASE_URL}/${normalizedPath}`
  }

  if (
    normalizedPath.startsWith("outputs/") ||
    normalizedPath.startsWith("artifacts/") ||
    normalizedPath.startsWith("docs/")
  ) {
    return `/${normalizedPath}`
  }

  return resolveRepositoryBlobUrl(normalizedPath)
}

export function resolveMarkdownUrl(href: string): string {
  if (/^https?:\/\//.test(href)) {
    return href
  }

  const repoPrefix = "/Users/claire/PycharmProjects/evidence-based-hdb-resale-market-analysis/"

  if (href.startsWith(repoPrefix)) {
    return resolveRepositoryBlobUrl(href.slice(repoPrefix.length))
  }

  if (href.startsWith("/outputs/") || href.startsWith("/artifacts/") || href.startsWith("/docs/")) {
    return resolvePublicAssetUrl(href)
  }

  if (href.startsWith("/src/")) {
    return resolveRepositoryBlobUrl(href)
  }

  return href
}
