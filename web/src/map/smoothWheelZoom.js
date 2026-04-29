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
      // Capture the mapPane's current pan offset so the gesture can
      // SCALE-AROUND the cursor without wiping the existing pan.
      // Prior code reset to (0,0,1), which caused the map to visually
      // teleport when the user wheeled while panned (common after a
      // flyToBounds or drag at high zoom).
      const bp = L.DomUtil.getPosition(map._mapPane) || L.point(0, 0);
      this._basePos = bp;

      // Clear any leftover CSS transforms on the renderer's SVG container
      // (Leaflet's _onZoom may have applied a scale/translate during a
      // prior animation that wasn't fully cleared by stop()).
      const overlay = map._panes.overlayPane;
      if (overlay) {
        const overlayChildren = overlay.children;
        for (let i = 0; i < overlayChildren.length; i++) {
          const child = overlayChildren[i];
          const pos = L.DomUtil.getPosition(child) || L.point(0, 0);
          L.DomUtil.setTransform(child, pos, 1);
        }
      }

      // Initialize tooltip/popup panes to identity so counter-transforms
      // start from a known baseline.
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
    const bp = this._basePos || L.point(0, 0);
    // Scale around mp while preserving the mapPane's pre-gesture pan offset.
    // Math derivation: if a point P (in container coords) was at mapPane local
    //   X = P - bp before, after applying transform `translate(T) scale(s)`
    //   it appears at T + X*s. Setting cursor's latlng (X = mp - bp) to stay
    //   at mp gives T = mp*(1-s) + bp*s.
    L.DomUtil.setTransform(
      map._mapPane,
      L.point(mp.x * (1 - s) + bp.x * s, mp.y * (1 - s) + bp.y * s),
      s
    );

    // Counter-transform child panes (tooltipPane, popupPane) so their content
    // appears unscaled and unshifted in container coords. Derived similarly:
    //   counter_translate = (bp - mp) * (1 - s) / s,  counter_scale = 1 / s
    const cs = 1 / s;
    const cx = (bp.x - mp.x) * (1 - s) / s;
    const cy = (bp.y - mp.y) * (1 - s) / s;
    if (map._panes.tooltipPane) L.DomUtil.setTransform(map._panes.tooltipPane, L.point(cx, cy), cs);
    if (map._panes.popupPane) L.DomUtil.setTransform(map._panes.popupPane, L.point(cx, cy), cs);
  },

  _settle() {
    const map = this._map;
    // Restore tooltip/popup panes to identity.
    if (map._panes.tooltipPane) L.DomUtil.setTransform(map._panes.tooltipPane, L.point(0, 0), 1);
    if (map._panes.popupPane) L.DomUtil.setTransform(map._panes.popupPane, L.point(0, 0), 1);
    // Restore mapPane to its pre-gesture pan offset (setView/_resetView below
    // will re-position it as needed for the new zoom).
    L.DomUtil.setTransform(map._mapPane, this._basePos || L.point(0, 0), 1);
    map._animatingZoom = false;
    map.setZoomAround(this._mouseLatLng, this._goalZoom, { animate: false });
    this._active = false;
    this._raf = null;
    this._goalZoom = null;
    this._fromZoom = null;
    this._viewZoom = null;
    this._basePos = null;
  },
});

L.Map.addInitHook('addHandler', 'smoothWheelZoom', SmoothWheelZoom);
