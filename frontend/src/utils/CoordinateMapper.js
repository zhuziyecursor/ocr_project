/**
 * PDF坐标转换工具
 * 根据CLAUDE.md第3节：禁止手动坐标计算，必须使用此类
 */

/**
 * PDF bbox [x1, y1, x2, y2] → Canvas绘制参数
 */
export function pdfToCanvas(bbox, pageHeight, scale) {
  const [x1, y1, x2, y2] = bbox;
  return {
    left: x1 * scale,
    top: (pageHeight - y2) * scale,
    width: (x2 - x1) * scale,
    height: (y2 - y1) * scale
  };
}

/**
 * Canvas坐标 → PDF坐标（用于点击反查）
 */
export function canvasToPdf(x, y, pageHeight, scale) {
  return {
    x: x / scale,
    y: pageHeight - (y / scale)
  };
}

export class CoordinateMapper {
  constructor(pdfPage, scale = 1.0) {
    this.pageHeight = pdfPage.view[3];
    this.scale = scale;
  }

  updateScale(newScale) {
    this.scale = newScale;
  }

  updatePageHeight(pageHeight) {
    this.pageHeight = pageHeight;
  }

  transform(bbox) {
    return pdfToCanvas(bbox, this.pageHeight, this.scale);
  }

  inverseTransform(x, y) {
    return canvasToPdf(x, y, this.pageHeight, this.scale);
  }
}

export default CoordinateMapper;
