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
    :class="['chart-placeholder', { active, 'need-review': block.need_review }]"
    @click="emit('click')"
    @dblclick="emit('dblclick')"
  >
    <div class="chart-icon">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M3 3v18h18" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M7 16l4-4 4 4 5-6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>

    <div class="chart-title" v-if="block.label || block.caption">
      {{ block.label || block.caption }}
    </div>

    <!-- AI description - this is all we can show per CLAUDE.md section 10 -->
    <div class="chart-description" v-if="block.description">
      {{ block.description }}
    </div>
    <div v-else class="chart-no-description">
      图表内容无法还原，仅显示 AI 文字描述
    </div>

    <div class="chart-type-badge" v-if="block.chart_type">
      {{ block.chart_type }}
    </div>

    <div v-if="block.need_review" class="review-badge">需核验</div>
    <div class="confidence" v-if="block.confidence != null">
      置信度 {{ (block.confidence * 100).toFixed(0) }}%
    </div>
  </div>
</template>

<style scoped>
.chart-placeholder {
  margin-bottom: 10px;
  padding: 20px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  transition: all 0.15s;
  position: relative;
  background: #fafafa;
  text-align: center;
}
.chart-placeholder:hover { background: #f0f0f0; border-color: #c0c0c0; }
.chart-placeholder.active { outline: 2px solid #409eff; border-color: #409eff; }
.chart-placeholder.need-review { background: #E3F2FD; border-color: #90caf9; }
.chart-icon { color: #999; margin-bottom: 12px; }
.chart-title { font-size: 13px; font-weight: 600; color: #333; margin-bottom: 8px; }
.chart-description { font-size: 13px; color: #555; background: white; padding: 12px; border-radius: 4px; line-height: 1.6; text-align: left; margin-top: 8px; border: 1px solid #eee; }
.chart-no-description { font-size: 12px; color: #999; margin-top: 8px; }
.chart-type-badge { position: absolute; top: 8px; right: 8px; background: #9e9e9e; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.review-badge { position: absolute; top: 8px; left: 8px; background: #ff9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.confidence { font-size: 11px; color: #999; margin-top: 8px; }
</style>