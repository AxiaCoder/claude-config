/** One question pinned above the prompt, awaiting the user's answer. */
export type OpenQuestion = {
  /** Stable handle the model passes to `unpin_question`. */
  id: string
  /** One line, at most 100 characters. */
  question: string
  /** Markdown shown in the details pane; absent when none was given. */
  context?: string
  /** 2 to 4 one-line choices, at most 30 characters each; absent for an open question. */
  options?: string[]
}

/** A question pinned earlier in the session, kept to recognise its answer tag in a draft. */
export type AskedQuestion = Pick<OpenQuestion, 'question' | 'options'>

declare module 'claude-code' {
  interface PluginState {
    'open-question': {
      questions: OpenQuestion[]
      nextId: number
      shownId: string | null
      asked: AskedQuestion[]
    }
  }
}
