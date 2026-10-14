// Chrome, Firefox and Safari word a failed dynamic import differently; all of them mean the file did not arrive.
const CHUNK_FAILURE = /dynamically imported module|importing a module script failed|loading (css )?chunk .* failed|ChunkLoadError/i
export function isChunkLoadError(error: unknown) { return error instanceof Error && CHUNK_FAILURE.test(error.name + ' ' + error.message) }
