<script setup>
const props = defineProps({
  block: { type: Object, required: true },
  active: { type: Boolean, default: false },
  editing: { type: Boolean, default: false }
})
const emit = defineEmits(['click', 'dblclick'])

// Helper to get table data from block
function getTableData() {
  const jsonData = props.block.table_data || props.block.table || null

  if (jsonData) {
    return { json: jsonData, html: null }
  }

  // Fallback: treat content as plain text table
  const content = props.block.content || props.block.text || ''
  const rows = content.split('\n').filter(r => r.trim())
  return {
    json: null,
    html: `<table><tbody><tr>${rows.map(r => `<td>${r}</td>`).join('')}</tr></tbody></table>`
  }
}

const tableInfo = getTableData()
</script>

<template>
  <div
    :class="['table-block', { active, 'need-review': block.need_review }]"
    @click="emit('click')"
    @dblclick="emit('dblclick')"
  >
    <div class="table-caption" v-if="block.label || block.caption">
      {{ block.label || block.caption }}
    </div>

    <!-- JSON table data -->
    <div v-if="tableInfo.json" class="table-wrapper">
      <table class="table-content">
        <thead v-if="tableInfo.json.headers">
          <tr>
            <th v-for="h in tableInfo.json.headers" :key="h">{{ h }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in tableInfo.json.rows" :key="ri">
            <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Fallback HTML table -->
    <div v-else-if="tableInfo.html" class="table-wrapper" v-html="tableInfo.html" />

    <!-- Empty state -->
    <div v-else class="empty-table">[表格内容为空]</div>

    <div v-if="block.need_review" class="review-badge">需核验</div>
    <div class="confidence" v-if="block.confidence != null">
      置信度 {{ (block.confidence * 100).toFixed(0) }}%
    </div>
  </div>
</template>

<style scoped>
.table-block {
  margin-bottom: 10px;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid #e8e8e8;
  transition: all 0.15s;
  position: relative;
}
.table-block:hover { background: #fafafa; border-color: #c0c0c0; }
.table-block.active { outline: 2px solid #409eff; border-color: #409eff; }
.table-block.need-review { background: #E3F2FD; border-color: #90caf9; }
.table-caption { font-size: 12px; color: #666; margin-bottom: 8px; font-style: italic; }
.table-wrapper { overflow-x: auto; }
.table-content { width: 100%; border-collapse: collapse; font-size: 13px; }
.table-content th, .table-content td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
.table-content th { background: #f5f5f5; font-weight: 600; }
.table-content tr:hover { background: #fafafa; }
.empty-table { color: #999; font-size: 13px; text-align: center; padding: 20px; }
.review-badge { position: absolute; top: 8px; right: 8px; background: #ff9800; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.confidence { font-size: 11px; color: #999; margin-top: 4px; text-align: right; }
</style>