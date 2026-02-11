import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Button, Space, Tooltip, Typography } from 'antd'
import { MinusOutlined, PlusOutlined, SearchOutlined, CompressOutlined, ExpandOutlined } from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import { Compartment, EditorState } from '@codemirror/state'
import {
  EditorView,
  ViewUpdate,
  highlightActiveLine,
  highlightActiveLineGutter,
  highlightSpecialChars,
  keymap,
  lineNumbers,
} from '@codemirror/view'
import {
  bracketMatching,
  defaultHighlightStyle,
  foldAll,
  foldGutter,
  foldKeymap,
  syntaxHighlighting,
  unfoldAll,
} from '@codemirror/language'
import { defaultKeymap } from '@codemirror/commands'
import {
  SearchQuery,
  closeSearchPanel,
  findNext,
  findPrevious,
  getSearchQuery,
  openSearchPanel,
  search,
  searchKeymap,
  selectMatches,
  setSearchQuery,
} from '@codemirror/search'
import { javascript } from '@codemirror/lang-javascript'
import { cpp } from '@codemirror/lang-cpp'
import { go } from '@codemirror/lang-go'
import { python } from '@codemirror/lang-python'
import { json } from '@codemirror/lang-json'
import { markdown } from '@codemirror/lang-markdown'
import { rust } from '@codemirror/lang-rust'
import { yaml } from '@codemirror/lang-yaml'

function pickLanguageExtension(filename?: string) {
  const name = (filename || '').toLowerCase()
  if (name.endsWith('.py')) return python()
  if (name.endsWith('.json')) return json()
  if (name.endsWith('.yaml') || name.endsWith('.yml')) return yaml()
  if (name.endsWith('.md') || name.endsWith('.markdown')) return markdown()

  if (
    name.endsWith('.c') ||
    name.endsWith('.h') ||
    name.endsWith('.cc') ||
    name.endsWith('.hh') ||
    name.endsWith('.cpp') ||
    name.endsWith('.hpp') ||
    name.endsWith('.cxx') ||
    name.endsWith('.hxx')
  )
    return cpp()

  if (name.endsWith('.go')) return go()
  if (name.endsWith('.rs')) return rust()

  if (name.endsWith('.ts')) return javascript({ typescript: true })
  if (name.endsWith('.tsx')) return javascript({ typescript: true, jsx: true })
  if (name.endsWith('.js')) return javascript({ typescript: false })
  if (name.endsWith('.jsx')) return javascript({ typescript: false, jsx: true })

  return null
}

export default function CodeTextViewer(props: { value: string; filename?: string; maxHeight?: number }) {
  const { t, i18n } = useTranslation()
  const parentRef = useRef<HTMLDivElement | null>(null)
  const viewRef = useRef<EditorView | null>(null)

  const toolbarButtonStyle: React.CSSProperties = {
    width: 32,
    height: 32,
    padding: 0,
    borderRadius: 10,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  }

  const [fontSize, setFontSize] = useState<number>(() => {
    const raw = localStorage.getItem('assets.code_viewer.font_size')
    const n = Number(raw)
    if (Number.isFinite(n) && n >= 10 && n <= 22) return n
    return 12
  })

  useEffect(() => {
    localStorage.setItem('assets.code_viewer.font_size', String(fontSize))
  }, [fontSize])

  const langCompartment = useMemo(() => new Compartment(), [])
  const themeCompartment = useMemo(() => new Compartment(), [])
  const searchCompartment = useMemo(() => new Compartment(), [])

  const langExtension = useMemo(() => pickLanguageExtension(props.filename), [props.filename])

  const searchExtension = useMemo(() => {
    const createPanel = (view: EditorView) => {
      const dom = document.createElement('form')
      dom.className = 'cm-search'

      const label = document.createElement('label')
      label.textContent = (t('assets.code_search.find') || 'Find') + ':'

      const input = document.createElement('input')
      input.className = 'cm-textfield'
      input.type = 'text'
      input.setAttribute('main-field', 'true')
      input.placeholder = t('assets.code_search.placeholder') || ''

      const btnPrev = document.createElement('button')
      btnPrev.className = 'cm-button'
      btnPrev.type = 'button'
      btnPrev.textContent = t('assets.code_search.previous') || 'Previous'

      const btnNext = document.createElement('button')
      btnNext.className = 'cm-button'
      btnNext.type = 'button'
      btnNext.textContent = t('assets.code_search.next') || 'Next'

      const btnAll = document.createElement('button')
      btnAll.className = 'cm-button'
      btnAll.type = 'button'
      btnAll.textContent = t('assets.code_search.all') || 'All'

      const btnClose = document.createElement('button')
      btnClose.className = 'cm-button'
      btnClose.type = 'button'
      btnClose.textContent = t('assets.code_search.close') || 'Close'

      const mkCheckbox = (key: string, fallback: string) => {
        const wrap = document.createElement('label')
        wrap.style.display = 'inline-flex'
        wrap.style.alignItems = 'center'
        wrap.style.gap = '6px'
        wrap.style.marginLeft = '6px'

        const cb = document.createElement('input')
        cb.type = 'checkbox'

        const text = document.createElement('span')
        text.textContent = t(key) || fallback

        wrap.appendChild(cb)
        wrap.appendChild(text)
        return { wrap, cb }
      }

      const optCase = mkCheckbox('assets.code_search.match_case', 'Match case')
      const optWord = mkCheckbox('assets.code_search.whole_word', 'Whole word')
      const optRegexp = mkCheckbox('assets.code_search.regexp', 'RegExp')

      const syncFromState = (state: EditorState) => {
        const q = getSearchQuery(state)
        const want = q.search || ''
        if (input.value !== want) input.value = want
        optCase.cb.checked = Boolean(q.caseSensitive)
        optWord.cb.checked = Boolean(q.wholeWord)
        optRegexp.cb.checked = Boolean(q.regexp)
      }

      const apply = () => {
        const prev = getSearchQuery(view.state)
        const next = new SearchQuery({
          search: input.value,
          caseSensitive: optCase.cb.checked,
          wholeWord: optWord.cb.checked,
          regexp: optRegexp.cb.checked,
          literal: prev.literal,
          replace: prev.replace,
        })
        view.dispatch({ effects: setSearchQuery.of(next) })
      }

      dom.addEventListener('submit', (e) => {
        e.preventDefault()
        apply()
        findNext(view)
      })

      input.addEventListener('input', () => apply())
      optCase.cb.addEventListener('change', () => apply())
      optWord.cb.addEventListener('change', () => apply())
      optRegexp.cb.addEventListener('change', () => apply())

      btnPrev.addEventListener('click', () => {
        apply()
        findPrevious(view)
      })
      btnNext.addEventListener('click', () => {
        apply()
        findNext(view)
      })
      btnAll.addEventListener('click', () => {
        apply()
        selectMatches(view)
      })
      btnClose.addEventListener('click', () => {
        closeSearchPanel(view)
      })

      dom.appendChild(label)
      dom.appendChild(input)
      dom.appendChild(btnPrev)
      dom.appendChild(btnNext)
      dom.appendChild(btnAll)
      dom.appendChild(btnClose)
      dom.appendChild(optCase.wrap)
      dom.appendChild(optWord.wrap)
      dom.appendChild(optRegexp.wrap)

      syncFromState(view.state)

      return {
        dom,
        top: true,
        update(update: ViewUpdate) {
          for (const tr of update.transactions) {
            if (tr.effects.some((e) => e.is(setSearchQuery))) {
              syncFromState(update.state)
              return
            }
          }
        },
      }
    }

    return search({ top: true, createPanel })
  }, [i18n.language])

  const themeExtension = useMemo(() => {
    const maxHeight = props.maxHeight ?? 520
    return EditorView.theme(
      {
        '&': {
          fontSize: `${fontSize}px`,
          height: '100%',
        },
        '.cm-editor': {
          backgroundColor: '#ffffff',
        },
        '.cm-scroller': {
          overflow: 'auto',
          maxHeight: `${maxHeight}px`,
          position: 'relative',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
          lineHeight: '1.55',
        },
        '.cm-content': {
          padding: '10px 12px',
          position: 'relative',
          zIndex: 2,
          background: 'transparent',
        },
        '.cm-selectionLayer': {
          mixBlendMode: 'normal',
          zIndex: 3,
          pointerEvents: 'none',
        },
        '.cm-selectionLayer .cm-selectionBackground': {
          background: 'rgba(22, 119, 255, 0.35)',
          opacity: 1,
          mixBlendMode: 'normal',
        },
        '&.cm-focused .cm-selectionLayer .cm-selectionBackground': {
          background: 'rgba(22, 119, 255, 0.45)',
          opacity: 1,
          mixBlendMode: 'normal',
        },
        '.cm-cursorLayer': {
          zIndex: 4,
          pointerEvents: 'none',
        },
        '.cm-editor ::selection': {
          backgroundColor: 'rgba(22, 119, 255, 0.28) !important',
        },
        '.cm-editor ::-moz-selection': {
          backgroundColor: 'rgba(22, 119, 255, 0.28) !important',
        },
        '.cm-gutters': {
          backgroundColor: '#fafafa',
          borderRight: '1px solid #e5e7eb',
          color: '#6b7280',
        },
        '.cm-activeLine': {
          backgroundColor: '#f8fafc',
        },
        '.cm-activeLineGutter': {
          backgroundColor: '#f3f4f6',
        },
        '.cm-foldGutter .cm-gutterElement': {
          paddingLeft: '4px',
          paddingRight: '4px',
        },
        '.cm-searchMatch': {
          backgroundColor: '#fff7d6',
          outline: '1px solid #ffd666',
        },
        '.cm-searchMatch.cm-searchMatch-selected': {
          backgroundColor: '#ffe7ba',
          outline: '1px solid #ffc069',
        },

        '.cm-panels': {
          backgroundColor: '#fafafa',
          color: '#111827',
        },
        '.cm-panels.cm-panels-top': {
          borderBottom: '1px solid #e5e7eb',
        },
        '.cm-panels.cm-panels-bottom': {
          borderTop: '1px solid #e5e7eb',
        },
        '.cm-panel': {
          padding: '8px 10px',
          fontSize: '12px',
        },
        '.cm-panel.cm-search': {
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          flexWrap: 'wrap',
          boxShadow: 'none',
        },
        '.cm-panel.cm-search label': {
          color: '#6b7280',
        },
        '.cm-panel.cm-search .cm-textfield': {
          height: '28px',
          padding: '0 10px',
          borderRadius: '8px',
          border: '1px solid #d9d9d9',
          outline: 'none',
          background: '#ffffff',
          color: '#111827',
          boxShadow: 'none',
        },
        '.cm-panel.cm-search .cm-textfield:focus': {
          borderColor: '#1677ff',
          boxShadow: '0 0 0 2px rgba(22, 119, 255, 0.15)',
        },
        '.cm-panel.cm-search .cm-button': {
          height: '28px',
          padding: '0 10px',
          borderRadius: '8px',
          border: '1px solid #d9d9d9',
          background: '#ffffff',
          color: '#111827',
          cursor: 'pointer',
        },
        '.cm-panel.cm-search .cm-button:hover': {
          background: '#f5f5f5',
          borderColor: '#c9cdd4',
        },
        '.cm-panel.cm-search .cm-button:active': {
          background: '#f0f0f0',
        },
        '.cm-panel.cm-search .cm-button:focus': {
          outline: 'none',
          boxShadow: '0 0 0 2px rgba(22, 119, 255, 0.15)',
          borderColor: '#1677ff',
        },
        '.cm-panel.cm-search input[type="checkbox"]': {
          transform: 'translateY(1px)',
        },
      },
      { dark: false },
    )
  }, [fontSize, props.maxHeight])

  const baseExtensions = useMemo(
    () => [
      lineNumbers(),
      highlightSpecialChars(),
      highlightActiveLine(),
      highlightActiveLineGutter(),
      bracketMatching(),
      foldGutter(),
      keymap.of([...searchKeymap, ...foldKeymap, ...defaultKeymap]),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      EditorState.readOnly.of(true),
    ],
    [],
  )

  useEffect(() => {
    const parent = parentRef.current
    if (!parent) return

    if (viewRef.current) return

    const state = EditorState.create({
      doc: props.value || '',
      extensions: [
        ...baseExtensions,
        langCompartment.of(langExtension ?? []),
        themeCompartment.of(themeExtension),
        searchCompartment.of(searchExtension),
      ],
    })

    viewRef.current = new EditorView({ state, parent })
  }, [
    props.value,
    baseExtensions,
    langCompartment,
    themeCompartment,
    searchCompartment,
    langExtension,
    themeExtension,
    searchExtension,
  ])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return

    view.dispatch({
      effects: [
        langCompartment.reconfigure(langExtension ?? []),
        themeCompartment.reconfigure(themeExtension),
        searchCompartment.reconfigure(searchExtension),
      ],
    })
  }, [langCompartment, themeCompartment, searchCompartment, langExtension, themeExtension, searchExtension])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return

    const next = props.value || ''
    const cur = view.state.doc.toString()
    if (next === cur) return

    view.dispatch({
      changes: { from: 0, to: view.state.doc.length, insert: next },
      selection: { anchor: 0 },
    })
  }, [props.value])

  useEffect(() => {
    return () => {
      if (viewRef.current) {
        viewRef.current.destroy()
        viewRef.current = null
      }
    }
  }, [])

  const clampFontSize = (n: number) => Math.max(10, Math.min(22, n))

  return (
    <div style={{ width: '100%' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
          padding: '6px 8px',
          border: '1px solid #e5e7eb',
          borderRadius: 10,
          background: '#fafafa',
        }}
      >
        <Space size={6} wrap>
          <Tooltip title={t('assets.code_viewer.search') || 'Search (Ctrl+F)'}>
            <Button
              type="default"
              size="small"
              icon={<SearchOutlined />}
              style={toolbarButtonStyle}
              onClick={() => {
                if (viewRef.current) openSearchPanel(viewRef.current)
              }}
            />
          </Tooltip>
          <Tooltip title={t('assets.code_viewer.fold_all') || 'Fold all'}>
            <Button
              type="default"
              size="small"
              icon={<CompressOutlined />}
              style={toolbarButtonStyle}
              onClick={() => {
                if (viewRef.current) foldAll(viewRef.current)
              }}
            />
          </Tooltip>
          <Tooltip title={t('assets.code_viewer.unfold_all') || 'Unfold all'}>
            <Button
              type="default"
              size="small"
              icon={<ExpandOutlined />}
              style={toolbarButtonStyle}
              onClick={() => {
                if (viewRef.current) unfoldAll(viewRef.current)
              }}
            />
          </Tooltip>
        </Space>

        <Space size={6} wrap align="center">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {t('assets.code_viewer.font_size') || 'Font size'}: {fontSize}px
          </Typography.Text>
          <Button
            type="default"
            size="small"
            style={toolbarButtonStyle}
            icon={<MinusOutlined />}
            onClick={() => setFontSize((s) => clampFontSize(s - 1))}
          />
          <Button
            type="default"
            size="small"
            style={toolbarButtonStyle}
            icon={<PlusOutlined />}
            onClick={() => setFontSize((s) => clampFontSize(s + 1))}
          />
        </Space>
      </div>
      <div
        ref={parentRef}
        style={{
          width: '100%',
          border: '1px solid #e5e7eb',
          borderRadius: 8,
          overflow: 'hidden',
          background: '#fff',
        }}
      />
    </div>
  )
}
