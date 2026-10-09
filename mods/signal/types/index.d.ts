/** The note shown above the prompt: one line, at most 100 characters; null when none. */
export type Note = string | null

declare module 'claude-code' {
  interface PluginState {
    signal: {
      note: Note
    }
  }
}
