export function normalizeAdExplorerSelectionId(
  value
) {
  return String(value ?? "")
    .trim()
    .toUpperCase()
}

function normalizeSelectionIds(values) {
  const seen = new Set()
  const result = []

  for (
    const value
    of Array.isArray(values) ? values : []
  ) {
    const id =
      normalizeAdExplorerSelectionId(value)

    if (!id || seen.has(id)) {
      continue
    }

    seen.add(id)
    result.push(id)
  }

  return result
}

export function resolveAdExplorerSelection({
  currentIds = [],
  clickedId = "",
  anchorId = "",
  visibleIds = [],
  ctrlKey = false,
  metaKey = false,
  shiftKey = false,
} = {}) {
  const current =
    normalizeSelectionIds(currentIds)

  const visible =
    normalizeSelectionIds(visibleIds)

  const clicked =
    normalizeAdExplorerSelectionId(clickedId)

  const anchor =
    normalizeAdExplorerSelectionId(anchorId)

  if (!clicked) {
    return {
      ids: current,
      anchorId: anchor,
    }
  }

  const additive = Boolean(
    ctrlKey || metaKey
  )

  if (shiftKey) {
    const start =
      visible.indexOf(anchor)

    const end =
      visible.indexOf(clicked)

    if (
      start >= 0
      && end >= 0
    ) {
      const low = Math.min(start, end)
      const high = Math.max(start, end)

      const range =
        visible.slice(low, high + 1)

      return {
        ids: additive
          ? normalizeSelectionIds([
              ...current,
              ...range,
            ])
          : range,
        anchorId: anchor,
      }
    }
  }

  if (additive) {
    if (current.includes(clicked)) {
      return {
        ids: current.filter(
          id => id !== clicked
        ),
        anchorId: clicked,
      }
    }

    return {
      ids: normalizeSelectionIds([
        ...current,
        clicked,
      ]),
      anchorId: clicked,
    }
  }

  return {
    ids: [clicked],
    anchorId: clicked,
  }
}

export function selectAllAdExplorerSelection(
  visibleIds
) {
  return normalizeSelectionIds(
    visibleIds
  )
}
