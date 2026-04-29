import { setState } from '../state/store.js';
import { showInfoPanel } from '../ui/infoPanel.js';

export function bindFeature(feature, layer) {
  layer.on({
    mouseover: (e) => {
      e.target.setStyle({ weight: 2.5, color: '#222', fillOpacity: 0.85 });
      e.target.bringToFront();
    },
    mouseout: (e) => {
      e.target.setStyle({ weight: 1, color: '#666', fillOpacity: 0.75 });
    },
    click: (e) => {
      const props = e.target.feature.properties;
      const id = props.GEOID || feature.id;
      setState({ selectedFeatureId: id });
      showInfoPanel(props);
    },
  });

  const name = feature.properties.NAME || feature.properties.name || feature.properties.GEOID;
  if (name) {
    layer.bindTooltip(String(name), { sticky: true, direction: 'top', offset: [0, -10] });
  }
}
