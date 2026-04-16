<script setup>
const props = defineProps({
  block: { type: Object, required: true },
  active: { type: Boolean, default: false },
  editing: { type: Boolean, default: false }
})
const emit = defineEmits(['click', 'dblclick'])
</script>

<template>
  <div
    :class="['text-block', { active, 'need-review': block.need_review }]"
    @click="emit('click')"
    @dblclick="emit('dblclick')"
  >
    <div class="block-content">{{ block.content || block.text || '' }}</div>
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
.block-content { font-size: 14px; line-height: 1.7; white-space: pre-wrap; word-break: break-all; }
.review-badge { position: absolute; top: 8px; right: 8px; background: #ff9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.confidence { font-size: 11px; color: #999; margin-top: 4px; text-align: right; }
</style>