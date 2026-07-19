(function exposeMouldingRender(globalObject) {
  function getStripCropRect(sourceWidth, sourceHeight, { prepared = false } = {}) {
    const width = Math.max(0, Math.round(Number(sourceWidth) || 0));
    const height = Math.max(0, Math.round(Number(sourceHeight) || 0));
    if (!width || !height) return { x: 0, y: 0, width, height };

    const aspect = width / height;
    if (prepared || aspect < 4) {
      return { x: 0, y: 0, width, height };
    }

    const x = Math.round(width * 0.04);
    const endX = Math.round(width * 0.78);
    return {
      x,
      y: 0,
      width: Math.max(1, endX - x),
      height,
    };
  }

  function getTileOverlap(facePixels, tileWidth) {
    const face = Math.max(0, Number(facePixels) || 0);
    const tile = Math.max(0, Number(tileWidth) || 0);
    if (!face || tile <= 2) return 0;
    return Math.round(Math.min(10, tile * 0.12, Math.max(2, face * 0.08)));
  }

  globalObject.MouldingRender = Object.freeze({ getStripCropRect, getTileOverlap });
}(typeof window === 'undefined' ? globalThis : window));
