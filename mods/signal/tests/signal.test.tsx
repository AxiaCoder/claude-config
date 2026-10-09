import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const NOTE = 'mcp__signal__note'
const SURFACES = ['terminal', 'desktop'] as const

const BAND_PROPS = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 10,
  bodyColumns: 60,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

/**
 * Stands for the engine beneath the plugin: draws an empty band.
 *
 * @param on the test's registrar
 */
const standInForBand = (on: On) => {
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Box } = $.ui.resolve(e)

    return <Box key="engine-band" />
  })
}

/**
 * Calls the `note` tool as the model would.
 *
 * @param $ the test's engine
 * @param input the tool's arguments
 * @returns what the call resolved to
 */
const call = ($: Engine, input: Record<string, unknown>) =>
  $.tool.call({ tool: NOTE, ...input }) as Promise<{ deny?: string; result?: unknown }>

/**
 * Reads the note the band shows on `surface`.
 *
 * @param $ the test's engine
 * @param surface where the band is mounted
 * @returns the text of the drawn note, or undefined when none is drawn
 */
const shownNote = async ($: Engine, surface: (typeof SURFACES)[number] = 'terminal') => {
  const ui = await $.ui.mount({ plugin: 'signal', surface, component: 'AbovePrompt', props: BAND_PROPS })
  const shown = (await ui.find({ type: 'Text', text: /💡/ }))?.text
  await ui.unmount()

  return shown
}

describe('note', () => {
  test('accepts one line and answers a string', async ($, on) => {
    standInForBand(on)
    const answer = await call($, { text: 'skill candidate: apply-verdicts' })
    expect(answer.deny).toBeUndefined()
    expect(typeof answer.result).toBe('string')
  })

  test('refuses an empty note', async ($, on) => {
    standInForBand(on)
    expect((await call($, { text: '   ' })).deny).toMatch(/non-empty string/)
    expect((await call($, {})).deny).toMatch(/non-empty string/)
    expect((await call($, { text: 42 })).deny).toMatch(/non-empty string/)
  })

  test('refuses a note on several lines', async ($, on) => {
    standInForBand(on)
    expect((await call($, { text: 'First line\nSecond line' })).deny).toMatch(/one line/)
  })

  test('refuses a note over 100 characters, after trimming', async ($, on) => {
    standInForBand(on)
    expect((await call($, { text: 'a'.repeat(101) })).deny).toMatch(/shorter/)
    expect((await call($, { text: ` ${'a'.repeat(100)} ` })).deny).toBeUndefined()
  })

  test('refuses a note holding a lone carriage return', async ($, on) => {
    standInForBand(on)
    expect((await call($, { text: 'First line\rSecond line' })).deny).toMatch(/one line/)
  })

  test('accepts exactly 100 characters and names the length past it', async ($, on) => {
    standInForBand(on)
    expect((await call($, { text: 'a'.repeat(100) })).deny).toBeUndefined()
    expect((await call($, { text: 'a'.repeat(101) })).deny).toMatch(/101 characters, the limit is 100/)
  })

  test('a refused note leaves the current one shown', async ($, on) => {
    standInForBand(on)
    await call($, { text: 'Kept' })
    await call($, { text: '' })
    await call($, { text: 'Two\nlines' })
    await call($, { text: 'a'.repeat(101) })
    expect(await shownNote($)).toBe('💡 Kept')
  })

  test('a second note replaces the first', async ($, on) => {
    standInForBand(on)
    await call($, { text: 'First' })
    await call($, { text: 'Second' })
    for (const surface of SURFACES) {
      expect(await shownNote($, surface)).toBe('💡 Second')
    }
  })
})

describe('band', () => {
  test('draws the note, trimmed, on one truncated line', async ($, on) => {
    standInForBand(on)
    await call($, { text: '  Worth a look  ' })
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'signal', surface, component: 'AbovePrompt', props: BAND_PROPS })
      const drawn = await ui.find({ type: 'Text', text: /💡/ })
      expect(drawn?.text).toBe('💡 Worth a look')
      expect(drawn?.props.wrap).toBe('truncate-end')
      await ui.unmount()
    }
  })

  test('draws nothing without a note', async ($, on) => {
    standInForBand(on)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'signal', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.find({ type: 'Text', text: /💡/ })).toBeUndefined()
      expect(await ui.find({ key: 'engine-band' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('keeps what the rest of the chain draws beside the note', async ($, on) => {
    on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
      const { Text } = $.ui.resolve(e)

      return <Text>Pinned question</Text>
    })
    await call($, { text: 'Worth a look' })
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'signal', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect((await ui.find({ type: 'Text', text: /💡/ }))?.text).toBe('💡 Worth a look')
      expect(await ui.find({ type: 'Text', text: 'Pinned question' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('steps aside for a survey', async ($, on) => {
    standInForBand(on)
    await call($, { text: 'Hidden by a survey' })
    const ui = await $.ui.mount({
      plugin: 'signal',
      surface: 'terminal',
      component: 'AbovePrompt',
      props: { ...BAND_PROPS, hasSurvey: true },
    })
    expect(await ui.find({ type: 'Text', text: /💡/ })).toBeUndefined()
    await ui.unmount()
  })
})

describe('prompt submit', () => {
  test('a sent prompt clears the note', async ($, on) => {
    standInForBand(on)
    on('prompt.submit', ($, e) => ({ text: e.text }))
    await call($, { text: 'Gone after the prompt' })
    const sent = await $.prompt.submit({ text: 'next', wait: false, origin: { kind: 'composer' } })
    expect(sent).toMatchObject({ text: 'next' })
    expect(await shownNote($)).toBeUndefined()
  })

  test('a dropped prompt keeps the note', async ($, on) => {
    standInForBand(on)
    on('prompt.submit', () => ({ drop: 'blocked by a settings hook' }))
    await call($, { text: 'Still here' })
    const sent = await $.prompt.submit({ text: 'next', wait: false, origin: { kind: 'composer' } })
    expect(sent).toMatchObject({ drop: 'blocked by a settings hook' })
    expect(await shownNote($)).toBe('💡 Still here')
  })

  test('a prompt sent after a dropped one clears the note', async ($, on) => {
    standInForBand(on)
    let blocked = true
    on('prompt.submit', ($, e) => (blocked ? { drop: 'blocked by a settings hook' } : { text: e.text }))
    await call($, { text: 'Survives the drop only' })
    await $.prompt.submit({ text: 'first', wait: false, origin: { kind: 'composer' } })
    expect(await shownNote($)).toBe('💡 Survives the drop only')
    blocked = false
    await $.prompt.submit({ text: 'second', wait: false, origin: { kind: 'composer' } })
    expect(await shownNote($)).toBeUndefined()
  })
})

describe('session end', () => {
  const REASONS = ['clear', 'resume', 'logout', 'prompt_input_exit', 'other'] as const

  for (const reason of REASONS) {
    test(`${reason} clears the note`, async ($, on) => {
      standInForBand(on)
      on('session.end', (_, e) => ({ sessionId: e.sessionId }))
      await call($, { text: 'Does not survive' })
      await $.session.end({ reason, sessionId: 'test-session', resume: { id: 'test-session' } })
      expect(await shownNote($)).toBeUndefined()
    })
  }
})

const ENGINE_SECTIONS = [
  { id: 'intro', text: 'intro', scope: 'shared' },
  { id: 'env', text: 'env', scope: 'session' },
] as const

/**
 * Builds the input of a prompt composed for a request offering `tools`.
 *
 * @param tools the names of the tools the request offers
 * @returns a complete `prompt.compose` input
 */
const composeInput = (tools: readonly string[]) => ({
  model: 'claude-opus-5-5',
  promptModel: 'claude-opus-5-5',
  surfaces: ['terminal'] as const,
  tools,
  outputStyle: null,
  traits: [],
})

describe('prompt', () => {
  test('adds the rule last, as a session section, when the request offers note', async ($, on) => {
    on('prompt.compose', () => ({ sections: ENGINE_SECTIONS }))

    const { sections } = await $.prompt.compose(composeInput(['Read', NOTE]))

    expect(sections.slice(0, -1)).toEqual([...ENGINE_SECTIONS])
    expect(sections[sections.length - 1]).toMatchObject({ id: 'signal:rule', scope: 'session' })
    expect(sections[sections.length - 1]?.text).toContain('never in a note')
  })

  test('leaves the sections as next(e) answered when the request lacks note', async ($, on) => {
    on('prompt.compose', () => ({ sections: ENGINE_SECTIONS }))

    const { sections } = await $.prompt.compose(composeInput(['Read']))

    expect(sections).toEqual([...ENGINE_SECTIONS])
  })
})
