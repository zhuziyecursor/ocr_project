<script setup>
import { computed } from 'vue'
import TextBlock from './TextBlock.vue'
import TableBlock from './TableBlock.vue'
import ImageBlock from './ImageBlock.vue'
import ChartPlaceholder from './ChartPlaceholder.vue'

const props = defineProps({
  blocks: { type: Array, default: () => [] },
  activeBlockId: String
})
const emit = defineEmits(['click-block', 'dblclick-block'])

function isActive(block) {
  return props.activeBlockId === (block.id || block.block_id)
}

function getBlockId(block) {
  return block.id || block.block_id
}

function handleClick(block) {
  emit('click-block', getBlockId(block))
}

function handleDblClick(block) {
  emit('dblclick-block', block)
}

// Route to appropriate sub-component based on block type
function getBlockComponent(block) {
  const type = block.type?.toLowerCase()
  if (type === 'table') return TableBlock
  if (type === 'image' || type === 'img') return ImageBlock
  if (type === 'chart' || type === 'figure') return ChartPlaceholder
  return TextBlock
}
</script>

<template>
  <div class="structured-viewer">
    <component
      v-for="block in blocks"
      :key="getBlockId(block)"
      :is="getBlockComponent(block)"
      :block="block"
      :active="isActive(block)"
      :data-block-id="getBlockId(block)"
      @click="handleClick(block)"
      @dblclick="handleDblClick(block)"
    />

    <div v-if="!blocks || blocks.length === 0" class="empty-tip">
      暂无识别内容
    </div>
  </div>
</template>

<style scoped>
.structured-viewer { height: 100%; overflow: auto; padding: 20px; background: white; }
.empty-tip { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }
</style>