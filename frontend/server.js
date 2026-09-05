import express from 'express';
import fetch from 'node-fetch';
import cors from 'cors';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const app = express();
const PORT = 5001;
const VITE_GOOGLE_API_KEY = process.env.VITE_GOOGLE_API_KEY;

// Validate API key
if (!VITE_GOOGLE_API_KEY) {
  console.error('ERROR: VITE_GOOGLE_API_KEY environment variable is not set');
  process.exit(1);
}

app.use(cors());

// Add request logging middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// 🔍 Search location using Google Places API (Text Search)
app.get('/api/search-location', async (req, res) => {
  const query = req.query.q;

  if (!query) {
    return res.status(400).json({ error: "Missing query param" });
  }

  try {
    const apiUrl = `https://maps.googleapis.com/maps/api/place/textsearch/json?query=${encodeURIComponent(query)}&key=${VITE_GOOGLE_API_KEY}`;

    const response = await fetch(apiUrl);
    
    if (!response.ok) {
      throw new Error(`Google API returned status ${response.status}`);
    }
    
    const data = await response.json();

    if (data.status && data.status !== 'OK' && data.status !== 'ZERO_RESULTS') {
      throw new Error(`Google API error: ${data.status} - ${data.error_message || 'Unknown error'}`);
    }

    const results = (data.results || []).map(place => ({
      placeName: place.name,
      placeAddress: place.formatted_address,
      latitude: place.geometry.location.lat,
      longitude: place.geometry.location.lng,
      placeId: place.place_id,
    }));

    res.json({ suggestedLocations: results });
  } catch (error) {
    console.error("Google Maps API error:", error);
    res.status(500).json({ 
      error: 'Failed to search locations',
      details: error.message 
    });
  }
});

// 📍 Get place details using Place ID
app.get('/api/place-details', async (req, res) => {
  const placeId = req.query.placeId;

  if (!placeId) {
    return res.status(400).json({ error: "Missing placeId param" });
  }

  try {
    const apiUrl = `https://maps.googleapis.com/maps/api/place/details/json?place_id=${encodeURIComponent(placeId)}&key=${VITE_GOOGLE_API_KEY}`;

    const response = await fetch(apiUrl);
    
    if (!response.ok) {
      throw new Error(`Google API returned status ${response.status}`);
    }
    
    const data = await response.json();

    if (data.status && data.status !== 'OK') {
      throw new Error(`Google API error: ${data.status} - ${data.error_message || 'Unknown error'}`);
    }

    res.json(data.result);
  } catch (error) {
    console.error("Place details error:", error);
    res.status(500).json({ 
      error: 'Failed to get place details',
      details: error.message 
    });
  }
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    port: PORT 
  });
});

app.listen(PORT, () => {
  console.log(`✅ Proxy server running at http://localhost:${PORT}`);
  console.log(`📍 Location search endpoint: http://localhost:${PORT}/api/search-location`);
  console.log(`🔍 Place details endpoint: http://localhost:${PORT}/api/place-details`);
});
