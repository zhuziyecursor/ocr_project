/**
 * 滚动同步器
 * 根据CLAUDE.md第5.2节：禁止用滚动百分比做同步滚动，必须使用锚点元素策略
 */

export class ScrollSyncer {
  constructor(sourcePanel, targetPanel, blockSelector = '[data-block-id]') {
    this.sourcePanel = sourcePanel;
    this.targetPanel = targetPanel;
    this.blockSelector = blockSelector;
    this.isScrolling = false;
    this.scrollTimeout = null;
  }

  syncScroll(activeBlockId = null) {
    if (this.isScrolling) return;
    this.isScrolling = true;

    try {
      const sourceRect = this.sourcePanel.getBoundingClientRect();
      const centerY = sourceRect.top + sourceRect.height / 2;

      if (activeBlockId) {
        const activeBlock = this.targetPanel.querySelector(`[data-block-id="${activeBlockId}"]`);
        if (activeBlock) {
          activeBlock.scrollIntoView({ block: 'center', behavior: 'smooth' });
          return;
        }
      }

      let closestBlock = null;
      let minDistance = Infinity;
      const blocks = this.targetPanel.querySelectorAll(this.blockSelector);

      blocks.forEach(block => {
        const blockRect = block.getBoundingClientRect();
        const blockCenterY = blockRect.top + blockRect.height / 2;
        const distance = Math.abs(blockCenterY - centerY);
        if (distance < minDistance) {
          minDistance = distance;
          closestBlock = block;
        }
      });

      if (closestBlock) {
        closestBlock.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }
    } finally {
      this.scrollTimeout = setTimeout(() => { this.isScrolling = false; }, 150);
    }
  }

  handleSourceScroll(activeBlockId = null) {
    if (this.scrollTimeout) clearTimeout(this.scrollTimeout);
    this.syncScroll(activeBlockId);
  }

  destroy() {
    if (this.scrollTimeout) clearTimeout(this.scrollTimeout);
    this.sourcePanel = null;
    this.targetPanel = null;
  }
}

export function findBlockAtViewportCenter(container, blockSelector = '[data-block-id]') {
  const containerRect = container.getBoundingClientRect();
  const centerY = containerRect.top + containerRect.height / 2;
  let closestBlock = null;
  let minDistance = Infinity;
  const blocks = container.querySelectorAll(blockSelector);

  blocks.forEach(block => {
    const blockRect = block.getBoundingClientRect();
    const blockCenterY = blockRect.top + blockRect.height / 2;
    const distance = Math.abs(blockCenterY - centerY);
    if (distance < minDistance) {
      minDistance = distance;
      closestBlock = block;
    }
  });

  return closestBlock ? closestBlock.dataset.blockId : null;
}

export default ScrollSyncer;
