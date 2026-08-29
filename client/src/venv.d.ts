/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string  // From .env (local dev)
  readonly VITE_API_URL?: string       // From environment variables
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
