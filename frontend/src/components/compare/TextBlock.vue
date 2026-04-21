<script setup>
import { computed } from 'vue'

const props = defineProps({
  block: { type: Object, required: true },
  active: { type: Boolean, default: false },
  editing: { type: Boolean, default: false }
})
const emit = defineEmits(['click', 'dblclick'])

// 判断是否为代码块
function isCodeLike(text, block) {
  if (!text) return false

  // 根据字体大小判断
  const fontSize = block.font_size || block['font size'] || 12
  if (fontSize <= 9) return true

  // 根据内容特征判断
  const codePatterns = [
    /[{}\[\]();]/,
    /\/\/|\/\*|\*\/|#\s/m,
    /["'`].*["'`]\s*:/,
    /^\s*(import|export|const|let|var|function|class|def |async|await)\s/m,
    /^\s*(if|else|for|while|return|switch|try|catch)\s*[({]/m,
    /[.#]\w+\s*[{:]/,
    /<\w+[^>]*>/,
    /\w+\s*=\s*['"`]?[\w\d]+['"`]?/,
  ]

  const matchCount = codePatterns.filter(p => p.test(text)).length
  if (text.length < 100 && matchCount >= 2) return true
  if (text.length > 50 && matchCount >= 3) return true
  if (text.includes('":') && text.includes('{')) return true

  return matchCount >= 4
}

const content = computed(() => props.block.content || props.block.text || '')
const codeLike = computed(() => isCodeLike(content.value, props.block))
</script>

<template>
  <div
    :class="['text-block', { active, 'need-review': block.need_review, 'code-like': codeLike }]"
    @click="emit('click')"
    @dblclick="emit('dblclick')"
  >
    <div class="block-content">{{ content }}</div>
    <div v-if="block.need_review" class="review-badge">需核验</div>
    <div class="confidence" v-if="block.confidence != null">
      置信度 {{ (block.confidence * 100).toFixed(0) }}%
    </div>
  </div>
</template>

<style scoped>
.text-block {
  margin-bottom: 10px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  transition: all 0.15s;
  position: relative;
}
.text-block:hover { background: #fafafa; border-color: #c0c0c0; }
.text-block.active { outline: 2px solid #409eff; border-color: #409eff; }
.text-block.need-review { background: #E3F2FD; border-color: #90caf9; }
.text-block.code-like {
  font-family: monospace;
  background: #f5f5f5;
  border-left: 3px solid #409eff;
  padding-left: 12px;
}
.block-content { font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-all; }
.text-block.code-like .block-content { font-size: 13px; }
.review-badge { position: absolute; top: 8px; right: 8px; background: #ff9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.confidence { font-size: 11px; color: #999; margin-top: 4px; text-align: right; }
</style>