/** One question pinned above the prompt, awaiting the user's answer. */
export type OpenQuestion = {
  /** Stable handle the model passes to `unpin_question`. */
  id: string
  /** One line, at most 100 characters. */
  question: string
  /** Markdown shown in the details pane; absent when none was given. */
  context?: string
}

declare module 'claude-code' {
  interface PluginState {
    'open-question': {
      questions: OpenQuestion[]
      nextId: number
      shownId: string | null
    }
  }
}
