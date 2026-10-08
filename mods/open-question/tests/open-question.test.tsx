import { describe, expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const PIN = 'mcp__open-question__pin_question'
const UNPIN = 'mcp__open-question__unpin_question'
const SURFACES = ['terminal', 'desktop'] as const

const BAND_PROPS = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 10,
  bodyColumns: 60,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

const PANE_PROPS = {
  title: 'Question',
  isFocused: false,
  bodyColumns: 60,
  placement: 'inline' as const,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

/**
 * Stands for the engine beneath the plugin: draws an empty band, answers pane
 * opens and closes, and records them.
 *
 * @param on the test's registrar
 * @returns the panes opened (by title) and closed (by id), in order
 */
const standInForPanes = (on: On) => {
  const opened: string[] = []
  const closed: string[] = []
  on('ui.render', { component: 'AbovePrompt' }, ($, e) => {
    const { Box } = $.ui.resolve(e)

    return <Box key="engine-band" />
  })
  on('ui.open', ($, e) => {
    opened.push(e.title ?? e.id)

    return { value: { isPlaced: true } }
  })
  on('ui.close', ($, e) => {
    closed.push(e.id)

    return { value: undefined }
  })

  return { opened, closed }
}

/**
 * Calls one of the mod's tools as the model would.
 *
 * @param $ the test's engine
 * @param tool the tool's full name
 * @param input the tool's arguments
 * @returns what the call resolved to
 */
const call = ($: Engine, tool: `mcp__${string}__${string}`, input: Record<string, unknown>) =>
  $.tool.call({ tool, ...input }) as Promise<{ deny?: string; result?: unknown }>

/**
 * Pins a question and returns its id, failing the test when refused.
 *
 * @param $ the test's engine
 * @param question the question
 * @param context its optional Markdown
 * @returns the id the tool answered
 */
const pin = async ($: Engine, question: string, context?: string): Promise<string> => {
  const answer = await call($, PIN, context === undefined ? { question } : { question, context })
  expect(answer.deny).toBeUndefined()

  expect(typeof answer.result).toBe('string')

  return answer.result as string
}

describe('pin_question', () => {
  test('refuses a question over 100 characters', async ($, on) => {
    standInForPanes(on)
    const answer = await call($, PIN, { question: 'a'.repeat(101) })
    expect(answer.deny).toMatch(/shorter/)
    expect((await call($, PIN, { question: 'a'.repeat(100) })).deny).toBeUndefined()
  })

  test('refuses a question on several lines', async ($, on) => {
    standInForPanes(on)
    const answer = await call($, PIN, { question: 'First line?\nSecond line?' })
    expect(answer.deny).toMatch(/one line/)
  })

  test('refuses a fourth open question', async ($, on) => {
    standInForPanes(on)
    await pin($, 'One?')
    await pin($, 'Two?')
    await pin($, 'Three?')
    const answer = await call($, PIN, { question: 'Four?' })
    expect(answer.deny).toMatch(/unpin one before pinning another/)
  })
})

describe('unpin_question', () => {
  test('removes the question from the band', async ($, on) => {
    standInForPanes(on)
    const id = await pin($, 'Keep the old route?')
    expect((await call($, UNPIN, { id })).deny).toBeUndefined()
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.find({ text: /Keep the old route/ })).toBeUndefined()
      await ui.unmount()
    }
  })

  test('answers a string, the only result shape a registered tool takes', async ($, on) => {
    standInForPanes(on)
    const id = await pin($, 'Merge now?')
    expect(id).toMatch(/^q\d+$/)
    const answer = await call($, UNPIN, { id })
    expect(answer.result).toBe(`Unpinned ${id}.`)
  })

  test('refuses an unknown id', async ($, on) => {
    standInForPanes(on)
    expect((await call($, UNPIN, { id: 'q42' })).deny).toMatch(/no pinned question/)
  })
})

describe('band', () => {
  test('draws nothing without a question', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await ui.findAll({ type: 'Button' })).toHaveLength(0)
      expect(await ui.find({ type: 'Text', text: /❓/ })).toBeUndefined()
      expect(await ui.find({ key: 'engine-band' })).toBeDefined()
      await ui.unmount()
    }
  })

  test('draws one line per question, details only with a context', async ($, on) => {
    standInForPanes(on)
    const bare = await pin($, 'Rename the table?')
    const rich = await pin($, 'Which cache?', '## Options\n\n- Redis\n- in memory')
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect((await ui.find({ type: 'Text', text: /Rename the table/ }))?.text).toContain('❓ Rename the table?')
      expect(await ui.find({ key: `details:${bare}` })).toBeUndefined()
      expect(await ui.find({ key: `remove:${bare}` })).toBeDefined()
      expect(await ui.find({ key: `details:${rich}` })).toBeDefined()
      expect(await ui.find({ key: `remove:${rich}` })).toBeDefined()
      await ui.unmount()
    }
  })

  test('cuts a long question to the band width', async ($, on) => {
    standInForPanes(on)
    const question = 'b'.repeat(100)
    const id = await pin($, question, 'More.')
    const props = { ...BAND_PROPS, bodyColumns: 50 }
    for (const surface of SURFACES) {
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props })
      const shown = (await ui.find({ type: 'Text', text: /❓/ }))?.text ?? ''
      expect(shown).toContain('…')
      expect(4 + shown.length + 1 + '[ détails ]'.length + 1 + '[ x ]'.length).toBeLessThanOrEqual(50)
      await ui.unmount()
    }
  })

  test('frames the questions under a title, only while one is open', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const empty = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      expect(await empty.find({ type: 'Text', text: 'En attente de ta réponse' })).toBeUndefined()
      expect(await empty.find({ key: 'frame' })).toBeUndefined()
      await empty.unmount()

      const id = await pin($, `Ready on ${surface}?`)
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      const frame = await ui.find({ key: 'frame' })
      expect(frame?.props.borderStyle).toBe('round')
      expect(await ui.find({ type: 'Text', text: 'En attente de ta réponse' })).toBeDefined()
      expect(await ui.find({ key: `row:${id}` })).toBeDefined()
      await ui.press({ key: `remove:${id}` })
      await ui.unmount()
    }
  })

  test('[x] removes the question', async ($, on) => {
    standInForPanes(on)
    for (const surface of SURFACES) {
      const id = await pin($, `Ship on ${surface}?`)
      const ui = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      await ui.press({ key: `remove:${id}` })
      expect(await ui.find({ key: `row:${id}` })).toBeUndefined()
      await ui.unmount()
      expect((await call($, UNPIN, { id })).deny).toMatch(/no pinned question/)
    }
  })

  test('[détails] opens the pane on the context, [x] closes it', async ($, on) => {
    const panes = standInForPanes(on)
    for (const surface of SURFACES) {
      const id = await pin($, `Which cache on ${surface}?`, '## Options\n\n- Redis')
      const band = await $.ui.mount({ plugin: 'open-question', surface, component: 'AbovePrompt', props: BAND_PROPS })
      await band.press({ key: `details:${id}` })
      expect(panes.opened).toContain(`Which cache on ${surface}?`)

      const pane = await $.ui.mount({
        plugin: 'open-question',
        surface,
        component: 'Pane',
        requestId: 'open-question',
        props: { ...PANE_PROPS, title: `Which cache on ${surface}?` },
      })
      const markdown = await pane.find({ type: 'Markdown' })
      expect(markdown?.props.text).toBe('## Options\n\n- Redis')

      await band.press({ key: `remove:${id}` })
      expect(panes.closed).toContain('open-question')
      expect(await pane.find({ type: 'Markdown' })).toBeUndefined()
      await pane.unmount()
      await band.unmount()
    }
  })
})
