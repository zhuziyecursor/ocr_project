import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

export const useCompareStore = defineStore('compare', () => {
  const documentA = ref(null)
  const documentB = ref(null)
  const resultA = ref(null)   // result_json for doc A
  const resultB = ref(null)   // result_json for doc B
  const diffs = ref([])
  const activeBlockId = ref(null)
  const currentDiffIndex = ref(0)

  const reviewedDiffs = computed(() => diffs.value.filter(d => d.reviewed))

  // 展平 A 的所有 blocks（Review 页单文档用）
  const blocksA = computed(() => {
    const json = resultA.value?.document?.json_content
    if (!json) return []
    const blocks = []
    // texts 是顶层数组，每项的 prov[0].page_no 提供页码
    for (const item of (json.texts || [])) {
      const prov = item.prov?.[0]
      const pageNo = prov?.page_no ?? prov?.page ?? 1
      const bbox = prov?.bbox
      blocks.push({
        ...item,
        _page: pageNo,
        block_id: item.self_ref?.replace('#/texts/', 'text_'),
        content: item.text,
        bbox: bbox ? [bbox.l, bbox.t, bbox.r, bbox.b] : null,
      })
    }
    // tables 顶层数组
    for (const item of (json.tables || [])) {
      const prov = item.prov?.[0]
      const pageNo = prov?.page_no ?? prov?.page ?? 1
      blocks.push({ ...item, _page: pageNo, _type: 'table', block_id: item.self_ref })
    }
    // pictures 顶层数组
    for (const item of (json.pictures || [])) {
      const prov = item.prov?.[0]
      const pageNo = prov?.page_no ?? prov?.page ?? 1
      const bbox = prov?.bbox
      blocks.push({
        ...item,
        _page: pageNo,
        _type: 'image',
        block_id: item.self_ref,
        content: item.text || item.caption || item.ocr_text || '',
        bbox: bbox ? [bbox.l, bbox.t, bbox.r, bbox.b] : null,
      })
    }
    return blocks
  })

  // 展平 B 的所有 blocks（Compare 页用）
  const blocksB = computed(() => {
    const json = resultB.value?.document?.json_content
    if (!json) return []
    const blocks = []
    for (const item of (json.texts || [])) {
      const prov = item.prov?.[0]
      const pageNo = prov?.page_no ?? prov?.page ?? 1
      const bbox = prov?.bbox
      blocks.push({
        ...item,
        _page: pageNo,
        block_id: item.self_ref?.replace('#/texts/', 'text_'),
        content: item.text,
        bbox: bbox ? [bbox.l, bbox.t, bbox.r, bbox.b] : null,
      })
    }
    for (const item of (json.tables || [])) {
      const prov = item.prov?.[0]
      const pageNo = prov?.page_no ?? prov?.page ?? 1
      blocks.push({ ...item, _page: pageNo, _type: 'table', block_id: item.self_ref })
    }
    for (const item of (json.pictures || [])) {
      const prov = item.prov?.[0]
      const pageNo = prov?.page_no ?? prov?.page ?? 1
      const bbox = prov?.bbox
      blocks.push({
        ...item,
        _page: pageNo,
        _type: 'image',
        block_id: item.self_ref,
        content: item.text || item.caption || item.ocr_text || '',
        bbox: bbox ? [bbox.l, bbox.t, bbox.r, bbox.b] : null,
      })
    }
    return blocks
  })

  // 基于 diffs 生成 A 侧高亮
  const highlightsA = computed(() =>
    diffs.value
      .filter(d => d.bbox_a && d.page_a != null)
      .map(d => ({
        id: d.id,
        blockId: d.block_id_a,
        bbox: d.bbox_a,
        type: d.need_review ? 'need_review' : d.diff_type,
        page: d.page_a,
      }))
  )

  // 基于 diffs 生成 B 侧高亮
  const highlightsB = computed(() =>
    diffs.value
      .filter(d => d.bbox_b && d.page_b != null)
      .map(d => ({
        id: d.id,
        blockId: d.block_id_b,
        bbox: d.bbox_b,
        type: d.need_review ? 'need_review' : d.diff_type,
        page: d.page_b,
      }))
  )

  // Review 页：单文档，高亮 need_review blocks
  const highlightsReview = computed(() =>
    blocksA.value
      .filter(b => b.need_review)
      .map(b => ({
        id: b.id || b.block_id,
        blockId: b.id || b.block_id,
        bbox: b.bbox,
        type: 'need_review',
        page: b._page,
      }))
      .filter(h => h.bbox)
  )

  async function loadDocument(docId) {
    documentA.value = await api.getDocument(docId)
    try {
      resultA.value = await api.getDocumentResult(docId)
    } catch {
      resultA.value = null
    }
  }

  async function loadDocuments(docAId, docBId) {
    const [docA, docB] = await Promise.all([
      api.getDocument(docAId),
      api.getDocument(docBId),
    ])
    documentA.value = docA
    documentB.value = docB
    const [rA, rB] = await Promise.all([
      api.getDocumentResult(docAId).catch(() => null),
      api.getDocumentResult(docBId).catch(() => null),
    ])
    resultA.value = rA
    resultB.value = rB
  }

  async function loadDiffs(docAId, docBId) {
    try {
      const resp = await api.compareDocuments(docAId, docBId)
      diffs.value = resp.diffs || []
    } catch {
      diffs.value = []
    }
  }

  function setActiveBlock(blockId) {
    activeBlockId.value = blockId
  }

  function goToPrevDiff() {
    if (currentDiffIndex.value > 0) {
      currentDiffIndex.value--
      const diff = diffs.value[currentDiffIndex.value]
      activeBlockId.value = diff?.block_id_a || diff?.block_id_b
    }
  }

  function goToNextDiff() {
    if (currentDiffIndex.value < diffs.value.length - 1) {
      currentDiffIndex.value++
      const diff = diffs.value[currentDiffIndex.value]
      activeBlockId.value = diff?.block_id_a || diff?.block_id_b
    }
  }

  async function markReviewed(blockId, originalContent, modifiedContent, pageNo) {
    const diff = diffs.value.find(d => d.block_id_a === blockId || d.block_id_b === blockId)
    if (diff) diff.reviewed = true

    // 同步更新 blocksA 里的 need_review 状态
    const block = blocksA.value.find(b => (b.id || b.block_id) === blockId)
    if (block) block.need_review = false

    await api.createReviewRecord({
      document_id: documentA.value?.id,
      block_id: blockId,
      page_no: pageNo,
      original_content: originalContent,
      modified_content: modifiedContent,
    })
  }

  function reset() {
    documentA.value = null
    documentB.value = null
    resultA.value = null
    resultB.value = null
    diffs.value = []
    activeBlockId.value = null
    currentDiffIndex.value = 0
  }

  return {
    documentA, documentB, resultA, resultB,
    diffs, activeBlockId, currentDiffIndex,
    blocksA, blocksB,
    highlightsA, highlightsB, highlightsReview,
    reviewedDiffs,
    loadDocument, loadDocuments, loadDiffs,
    setActiveBlock, goToPrevDiff, goToNextDiff, markReviewed, reset,
  }
})
