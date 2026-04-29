import L from 'leaflet';

L.Map.mergeOptions({
  smoothWheelZoom: true,
  smoothSensitivity: 1,
});

const SmoothWheelZoom = L.Handler.extend({
  addHooks() {
    L.DomEvent.on(this._map._container, 'wheel', this._onWheel, this);
  },
  removeHooks() {
    L.DomEvent.off(this._map._container, 'wheel', this._onWheel, this);
  },

  _onWheel(e) {
    L.DomEvent.preventDefault(e);
    L.DomEvent.stopPropagation(e);
    const map = this._map;
    const delta = L.DomEvent.getWheelDelta(e) * 0.003 * (map.options.smoothSensitivity || 1);
    const newMousePoint = map.mouseEventToContainerPoint(e);

    // If a gesture is active but the cursor has jumped to a different area,
    // commit the current visible state and start a fresh gesture from the
    // new cursor position. Prevents the post-settle setZoomAround() from
    // anchoring at the stale original location, which "teleports" the view.
    if (this._active) {
      const dist = newMousePoint.distanceTo(this._mousePoint);
      if (dist > 60) {
        if (this._raf) {
          cancelAnimationFrame(this._raf);
          this._raf = null;
        }
        clearTimeout(this._timer);
        this._wheeling = false;
        this._goalZoom = this._viewZoom; // freeze at current visual zoom
        this._settle(); // commits with old anchor, sets _active = false
      }
    }

    if (!this._active) {
      if (map.stop) map.stop();
      L.DomUtil.setTransform(map._mapPane, L.point(0, 0), 1);
      if (map._panes.tooltipPane) L.DomUtil.setTransform(map._panes.tooltipPane, L.point(0, 0), 1);
      if (map._panes.popupPane) L.DomUtil.setTransform(map._panes.popupPane, L.point(0, 0), 1);
      map._animatingZoom = false;

      this._fromZoom = map.getZoom();
      this._viewZoom = this._fromZoom;
      this._goalZoom = this._fromZoom;
      this._mousePoint = newMousePoint;
      this._mouseLatLng = map.containerPointToLatLng(this._mousePoint);
      this._active = true;
    }
    this._wheeling = true;

    this._goalZoom = map._limitZoom(this._goalZoom + delta);

    clearTimeout(this._timer);
    this._timer = setTimeout(() => { this._wheeling = false; }, 200);

    if (!this._raf) {
      this._raf = requestAnimationFrame(() => this._tick());
    }
  },

  _tick() {
    this._raf = null;
    if (!this._active) return;

    const diff = this._goalZoom - this._viewZoom;
    const settled = !this._wheeling && Math.abs(diff) < 0.005;

    if (settled) {
      this._viewZoom = this._goalZoom;
      this._applyTransform();
      this._settle();
      return;
    }

    this._viewZoom += diff * 0.3;
    this._applyTransform();
    this._raf = requestAnimationFrame(() => this._tick());
  },

  _applyTransform() {
    const map = this._map;
    const s = map.getZoomScale(this._viewZoom, this._fromZoom);
    const mp = this._mousePoint;
    L.DomUtil.setTransform(map._mapPane, L.point(mp.x * (1 - s), mp.y * (1 - s)), s);

    const counterOffset = L.point((-mp.x * (1 - s)) / s, (-mp.y * (1 - s)) / s);
    const counterScale = 1 / s;
    if (map._panes.tooltipPane) L.DomUtil.setTransform(map._panes.tooltipPane, counterOffset, counterScale);
    if (map._panes.popupPane) L.DomUtil.setTransform(map._panes.popupPane, counterOffset, counterScale);
  },

  _settle() {
    const map = this._map;
    L.DomUtil.setTransform(map._mapPane, L.point(0, 0), 1);
    if (map._panes.tooltipPane) L.DomUtil.setTransform(map._panes.tooltipPane, L.point(0, 0), 1);
    if (map._panes.popupPane) L.DomUtil.setTransform(map._panes.popupPane, L.point(0, 0), 1);
    map._animatingZoom = false;
    map.setZoomAround(this._mouseLatLng, this._goalZoom, { animate: false });
    this._active = false;
    this._raf = null;
    this._goalZoom = null;
    this._fromZoom = null;
    this._viewZoom = null;
  },
});

L.Map.addInitHook('addHandler', 'smoothWheelZoom', SmoothWheelZoom);
