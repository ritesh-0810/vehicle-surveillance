// src/components/ResultsMap.jsx

import React from 'react';
import { GoogleMap, Marker, Polyline } from '@react-google-maps/api';

// Map container style
const containerStyle = {
  width: '100%',
  height: '100%'
};

// Options to customize the Polyline (the path)
const polylineOptions = {
  strokeColor: '#FF0000', // Red color for the line
  strokeOpacity: 0.8,
  strokeWeight: 2,
};

const ResultsMap = ({ detections }) => {
  // 1. Create the path for the Polyline from your detection data
  const path = detections.map(detection => ({
    lat: detection.latitude,
    lng: detection.longitude
  }));

  // 2. Calculate the center of the map to show all markers
  const getCenter = () => {
    if (path.length === 0) return { lat: 20.5937, lng: 78.9629 }; // Default to center of India
    const lat = path.reduce((sum, point) => sum + point.lat, 0) / path.length;
    const lng = path.reduce((sum, point) => sum + point.lng, 0) / path.length;
    return { lat, lng };
  };

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={getCenter()}
      zoom={12} // Adjust zoom as needed
    >
      {/* 3. Render a Marker for each detection point */}
      {detections.map((detection, index) => (
        <Marker
          key={detection._id || index}
          position={{ lat: detection.latitude, lng: detection.longitude }}
          label={(index + 1).toString()} // Label markers as 1, 2, 3...
        />
      ))}

      {/* 4. Render the Polyline to connect the markers */}
      {path.length > 1 && (
        <Polyline
          path={path}
          options={polylineOptions}
        />
      )}
    </GoogleMap>
  );
};

export default ResultsMap;