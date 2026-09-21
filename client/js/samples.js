/**
 * Sample Crop Damage Presets using real field photography from assets/
 * Real test images:
 * - assets/drought.webp (Severe Drought / Parched Soil)
 * - assets/flood.jpeg (Monsoon Flood / Submerged Lodged Paddy)
 * - assets/healthy.jpg (Healthy Vibrant Crop Rows)
 */

/**
 * Loads an image from path and converts to Base64 Data URL
 */
async function loadAssetAsDataUrl(imagePath) {
  try {
    const res = await fetch(imagePath);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  } catch (err) {
    console.error(`Failed to load asset ${imagePath}:`, err);
    return null;
  }
}

const SAMPLE_PRESETS = [
  {
    id: 'drought',
    title: 'Severe Drought',
    description: 'Parched soil with 78% heat & water-deficit loss',
    imagePath: 'assets/drought.webp',
    filename: 'drought.webp (538.9 KB)',
    dataUrl: null,
    formData: {
      farmerId: 'FARM-9021',
      fieldId: 'FIELD-NORTH-04',
      cropType: 'Wheat',
      claimedDamage: 78,
      latitude: 28.6139,
      longitude: 77.2090,
      lossDate: new Date(Date.now() - 5 * 86400000).toISOString().split('T')[0],
      rainfall: 0.8,
      temperature: 42.1,
      droughtIndex: 0.88,
      historicalYield: 'poor',
      claimFrequency: 1,
      fieldBoundary: [
        [28.6110, 77.2060],
        [28.6170, 77.2060],
        [28.6170, 77.2120],
        [28.6110, 77.2120]
      ],
    },
  },
  {
    id: 'flood',
    title: 'Monsoon Flood',
    description: 'Waterlogged paddy with 65% lodging damage',
    imagePath: 'assets/flood.jpeg',
    filename: 'flood.jpeg (85.0 KB)',
    dataUrl: null,
    formData: {
      farmerId: 'FARM-4482',
      fieldId: 'FIELD-EAST-12',
      cropType: 'Rice',
      claimedDamage: 65,
      latitude: 22.5726,
      longitude: 88.3639,
      lossDate: new Date(Date.now() - 3 * 86400000).toISOString().split('T')[0],
      rainfall: 135.0,
      temperature: 26.5,
      droughtIndex: 0.02,
      historicalYield: 'variable',
      claimFrequency: 2,
      fieldBoundary: [
        [22.5700, 88.3610],
        [22.5750, 88.3610],
        [22.5750, 88.3670],
        [22.5700, 88.3670]
      ],
    },
  },
  {
    id: 'healthy',
    title: 'Healthy Crop',
    description: 'Vibrant green canopy with minimal stress',
    imagePath: 'assets/healthy.jpg',
    filename: 'healthy.jpg (117.3 KB)',
    dataUrl: null,
    formData: {
      farmerId: 'FARM-1088',
      fieldId: 'FIELD-SOUTH-02',
      cropType: 'Rice',
      claimedDamage: 12,
      latitude: 16.5130,
      longitude: 80.6235,
      lossDate: new Date().toISOString().split('T')[0],
      rainfall: 18.5,
      temperature: 28.0,
      droughtIndex: 0.15,
      historicalYield: 'normal',
      claimFrequency: 0,
      fieldBoundary: [
        [16.5105, 80.6202],
        [16.5158, 80.6205],
        [16.5161, 80.6268],
        [16.5108, 80.6265]
      ],
    },
  },
];

// Pre-load all preset images into memory immediately on script load
SAMPLE_PRESETS.forEach(async (preset) => {
  preset.dataUrl = await loadAssetAsDataUrl(preset.imagePath);
});

window.loadAssetAsDataUrl = loadAssetAsDataUrl;
window.SamplePresets = SAMPLE_PRESETS;
