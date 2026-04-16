<script setup>
const props = defineProps({
  block: { type: Object, required: true },
  active: { type: Boolean, default: false },
  editing: { type: Boolean, default: false }
})
const emit = defineEmits(['click', 'dblclick'])

// Calculate image dimensions from bbox
function getImageStyle() {
  const bbox = props.block.bbox
  if (bbox && bbox.length === 4) {
    const width = (bbox[2] - bbox[0])
    const height = (bbox[3] - bbox[1])
    return {
      width: width > 0 ? `${width}px` : 'auto',
      height: height > 0 ? `${height}px` : 'auto'
    }
  }
  return {}
}

// Get image source URL
function getImageSrc() {
  // Prefer base64 embedded image
  if (props.block.image_data) {
    return `data:image/png;base64,${props.block.image_data}`
  }
  if (props.block.image_url) {
    return props.block.image_url
  }
  if (props.block.src) {
    return props.block.src
  }
  return null
}

const imageSrc = getImageSrc()
const imageStyle = getImageStyle()
</script>

<template>
  <div
    :class="['image-block', { active, 'need-review': block.need_review }]"
    @click="emit('click')"
    @dblclick="emit('dblclick')"
  >
    <div class="image-caption" v-if="block.label || block.caption">
      {{ block.label || block.caption }}
    </div>

    <div v-if="imageSrc" class="image-wrapper">
      <img :src="imageSrc" :style="imageStyle" class="block-image" />
    </div>

    <!-- AI description for image -->
    <div v-if="block.description" class="image-description">
      {{ block.description }}
    </div>

    <!-- Placeholder when no image -->
    <div v-else class="empty-image">[图片内容为空]</div>

    <div v-if="block.need_review" class="review-badge">需核验</div>
    <div class="confidence" v-if="block.confidence != null">
      置信度 {{ (block.confidence * 100).toFixed(0) }}%
    </div>
  </div>
</template>

<style scoped>
.image-block {
  margin-bottom: 10px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  transition: all 0.15s;
  position: relative;
}
.image-block:hover { background: #fafafa; border-color: #c0c0c0; }
.image-block.active { outline: 2px solid #409eff; border-color: #409eff; }
.image-block.need-review { background: #E3F2FD; border-color: #90caf9; }
.image-caption { font-size: 12px; color: #666; margin-bottom: 8px; font-style: italic; }
.image-wrapper { display: flex; justify-content: flex-start; }
.block-image { max-width: 100%; height: auto; border-radius: 4px; }
.image-description { margin-top: 8px; font-size: 13px; color: #555; background: #f9f9f9; padding: 8px; border-radius: 4px; line-height: 1.5; }
.empty-image { color: #999; font-size: 13px; text-align: center; padding: 20px; background: #f5f5f5; border-radius: 4px; }
.review-badge { position: absolute; top: 8px; right: 8px; background: #ff9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.confidence { font-size: 11px; color: #999; margin-top: 4px; text-align: right; }
</style>