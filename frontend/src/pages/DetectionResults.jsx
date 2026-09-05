"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend, ScatterChart, Scatter, ZAxis } from 'recharts'
import Button from "../components/Button"
import styles from "./DetectionResults.module.css"
import { generateDetectionReport } from "../utils/pdf-generator"
import { GoogleMap, useJsApiLoader, DirectionsRenderer, Marker } from "@react-google-maps/api"

const mapContainerStyle = {
  width: "100%",
  height: "100%",
}

const centerDefault = { lat: 20.5937, lng: 78.9629 }
const libraries = ["places", "directions"]

// Helper function to normalize license plate by removing whitespaces
const normalizeLicensePlate = (licensePlate) => {
  return licensePlate.replace(/\s+/g, "").toUpperCase();
}

const COLORS = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6'];

const DetectionResults = ({ detectionResults }) => {
  const [selectedDetection, setSelectedDetection] = useState(null)
  const [isGeneratingPDF, setIsGeneratingPDF] = useState(false)
  const [directionsResponse, setDirectionsResponse] = useState(null)
  const [orderedDetections, setOrderedDetections] = useState([])
  const [markers, setMarkers] = useState([])
  const [activeTab, setActiveTab] = useState("map")
  const mapRef = useRef(null)
  const mapContainerRef = useRef(null)
  const navigate = useNavigate()

  // Load the Google Maps JS API with necessary libraries
  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
    libraries,
    id: "google-map-script",
    language: "en",
    region: "US",
  })

  useEffect(() => {
    if (!detectionResults) {
      navigate("/search")
    }
  }, [detectionResults, navigate])

  const handleGeneratePDF = async () => {
    if (!detectionResults) return

    try {
      setIsGeneratingPDF(true)
      const pdf = await generateDetectionReport(detectionResults, mapContainerRef.current)
      if (pdf) {
        pdf.save(`vehicle_report_${normalizeLicensePlate(detectionResults.licensePlate)}.pdf`)
      } else {
        throw new Error("Failed to generate PDF")
      }
    } catch (error) {
      console.error("Error generating PDF:", error)
      alert("Failed to generate PDF report")
    } finally {
      setIsGeneratingPDF(false)
    }
  }

  // Clean up function for markers
  const clearMarkers = useCallback(() => {
    if (markers.length > 0) {
      markers.forEach((marker) => {
        if (marker && marker.setMap) {
          marker.setMap(null)
        }
      })
      setMarkers([])
    }
  }, [markers])

  // Create markers function
  const createMarkers = useCallback(
    (map) => {
      if (!map || !window.google || !window.google.maps || !detectionResults?.detections) {
        return
      }

      // Clear any existing markers
      clearMarkers()

      const validDetections = detectionResults.detections.filter((d) => d.coordinates?.lat && d.coordinates?.lng)

      // Create new markers
      const newMarkers = validDetections.map((detection, index) => {
        const marker = new window.google.maps.Marker({
          position: {
            lat: detection.coordinates.lat,
            lng: detection.coordinates.lng,
          },
          map,
          title: `Detection ${index + 1}`,
          animation: window.google.maps.Animation.DROP,
          icon: {
            path: window.google.maps.SymbolPath.CIRCLE,
            fillColor: '#3498db',
            fillOpacity: 0.9,
            strokeWeight: 2,
            strokeColor: '#ffffff',
            scale: 8,
          }
        })

        marker.addListener("click", () => {
          setSelectedDetection(detection.id)
        })

        return marker
      })

      setMarkers(newMarkers)
    },
    [detectionResults, clearMarkers],
  )

  const handleMapLoad = useCallback(
    (map) => {
      if (!map || !window.google || !window.google.maps) return

      mapRef.current = map

      // Setup bounds
      try {
        const bounds = new window.google.maps.LatLngBounds()
        let hasValidCoordinates = false

        if (detectionResults?.detections) {
          detectionResults.detections.forEach((detection) => {
            if (detection.coordinates?.lat && detection.coordinates?.lng) {
              bounds.extend({
                lat: detection.coordinates.lat,
                lng: detection.coordinates.lng,
              })
              hasValidCoordinates = true
            }
          })
        }

        if (hasValidCoordinates) {
          map.fitBounds(bounds)
          // Add some padding to the bounds
          const padding = { top: 50, right: 50, bottom: 50, left: 50 }
          map.fitBounds(bounds, padding)
        } else {
          map.setCenter(centerDefault)
          map.setZoom(5)
        }

        // Create markers after bounds are set
        createMarkers(map)
      } catch (error) {
        console.error("Error setting up map:", error)
        map.setCenter(centerDefault)
        map.setZoom(5)
      }
    },
    [detectionResults, createMarkers],
  )

  // Handle directions calculation
  useEffect(() => {
    if (!isLoaded || !window.google || !window.google.maps || !detectionResults?.detections) {
      return
    }

    const validDetections = detectionResults.detections.filter((d) => d.coordinates?.lat && d.coordinates?.lng)

    // Need at least origin and destination
    if (validDetections.length < 2) {
      setOrderedDetections(detectionResults.detections || [])
      return
    }

    const path = validDetections.map((d) => ({
      lat: d.coordinates.lat,
      lng: d.coordinates.lng,
    }))

    try {
      const directionsService = new window.google.maps.DirectionsService()

      directionsService.route(
        {
          origin: path[0],
          destination: path[path.length - 1],
          travelMode: window.google.maps.TravelMode.DRIVING,
          waypoints: path.slice(1, -1).map((loc) => ({ location: loc })),
          optimizeWaypoints: true,
        },
        (result, status) => {
          if (status === window.google.maps.DirectionsStatus.OK) {
            setDirectionsResponse(result)

            // Re-order detections based on optimized waypoints
            const { waypoint_order } = result.routes[0]
            const reordered = [
              validDetections[0], // origin
              ...waypoint_order.map((i) => validDetections[i + 1]), // optimized waypoints
              validDetections[validDetections.length - 1], // destination
            ]
            setOrderedDetections(reordered)
          } else {
            console.error("Directions request failed:", status)
            // Fallback to default order if directions fail
            setOrderedDetections(detectionResults.detections || [])
          }
        },
      )
    } catch (error) {
      console.error("Error with directions service:", error)
      setOrderedDetections(detectionResults.detections || [])
    }
  }, [isLoaded, detectionResults])

  // Clean up markers when component unmounts
  useEffect(() => {
    return clearMarkers
  }, [clearMarkers])

  const getDetectionFrequencyData = () => {
    if (!detectionResults?.detections) return [];
    
    // Group detections by day
    const frequencyMap = detectionResults.detections.reduce((acc, detection) => {
      const date = new Date(detection.timestamp);
      const key = date.toISOString().split('T')[0]; // YYYY-MM-DD
      
      if (!acc[key]) {
        acc[key] = 0;
      }
      acc[key]++;
      return acc;
    }, {});

    // Convert to array for the chart
    return Object.entries(frequencyMap).map(([date, count]) => ({
      date,
      count,
    })).sort((a, b) => new Date(a.date) - new Date(b.date));
  };

  const getTimeOfDayData = () => {
    if (!detectionResults?.detections) return [];
    
    // Group detections by hour of day
    const hours = Array(24).fill(0).map((_, i) => ({ hour: i, count: 0 }));
    
    detectionResults.detections.forEach(detection => {
      const date = new Date(detection.timestamp);
      const hour = date.getHours();
      hours[hour].count++;
    });
    
    return hours;
  };

  const getLocationFrequencyData = () => {
    if (!detectionResults?.detections) return [];
    
    const locationMap = detectionResults.detections.reduce((acc, detection) => {
      const location = detection.location || 'Unknown';
      if (!acc[location]) {
        acc[location] = 0;
      }
      acc[location]++;
      return acc;
    }, {});
    
    return Object.entries(locationMap)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5); // Top 5 locations
  };

  const getSpeedAnalysisData = () => {
    if (!detectionResults?.detections) return [];
    
    // Filter detections with speed data and group by hour
    const speedData = detectionResults.detections
      .filter(d => d.speed !== undefined && d.speed !== null)
      .map(d => {
        const date = new Date(d.timestamp);
        return {
          hour: date.getHours(),
          speed: d.speed,
          timestamp: d.timestamp
        };
      });
    
    return speedData;
  };

  const frequencyData = getDetectionFrequencyData();
  const timeOfDayData = getTimeOfDayData();
  const locationData = getLocationFrequencyData();
  const speedData = getSpeedAnalysisData();

  if (loadError) {
    return (
      <div className={styles.error}>
        <h2>Error loading Google Maps</h2>
        <p>{loadError.message}</p>
        <p>Please check your internet connection or API key configuration.</p>
        <Button onClick={() => window.location.reload()} variant="primary">
          Retry
        </Button>
      </div>
    )
  }

  if (!isLoaded) {
    return (
      <div className={styles.loading}>
        <div className={styles.loadingSpinner}></div>
        <p>Loading map components...</p>
      </div>
    )
  }

  if (!detectionResults) {
    return <div className={styles.noData}>No detection data available</div>
  }

  return (
    <div className={styles.dashboardContainer}>
      <div className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.plateIcon}></div>
          <div className={styles.plateDetails}>
            <h2>{detectionResults.licensePlate}</h2>
            <p>
              {detectionResults.detections.length} detection{detectionResults.detections.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className={styles.detectionList}>
          <div className={styles.listHeader}>
            <h3>Detection Timeline</h3>
            {orderedDetections.length > 0 && <span className={styles.optimizedBadge}>Optimized</span>}
          </div>

          {(orderedDetections.length > 0 ? orderedDetections : detectionResults.detections).map((detection, index) => (
            <div
              key={detection.id || index}
              className={`${styles.detectionItem} ${selectedDetection === detection.id ? styles.selected : ""}`}
              onClick={() => setSelectedDetection(detection.id)}
            >
              <div className={styles.detectionHeader}>
                <div className={styles.detectionTime}>
                  <span className={styles.timeIcon}></span>
                  {new Date(detection.timestamp).toLocaleString()}
                </div>
                <div className={styles.detectionBadge}>#{index + 1}</div>
              </div>
              <div className={styles.detectionLocation}>
                <span className={styles.locationIcon}></span>
                {detection.location}
              </div>
              {detection.speed && (
                <div className={styles.detectionSpeed}>
                  <span className={styles.speedIcon}></span>
                  {detection.speed} km/h
                </div>
              )}
            </div>
          ))}
        </div>

        <div className={styles.sidebarActions}>
          <Button onClick={handleGeneratePDF} disabled={isGeneratingPDF} fullWidth>
            {isGeneratingPDF ? (
              <span className={styles.loadingWrapper}>
                <span className={styles.loadingDot}></span>
                <span className={styles.loadingDot}></span>
                <span className={styles.loadingDot}></span>
                <span>Generating</span>
              </span>
            ) : (
              <span className={styles.buttonContent}>Generate PDF Report</span>
            )}
          </Button>
        </div>
      </div>

      <div className={styles.mainContent}>
        <div className={styles.dashboardHeader}>
          <h1>Detection Results</h1>
          <div className={styles.tabsContainer}>
            <button
              className={`${styles.tabButton} ${activeTab === "map" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("map")}
            >
              <span className={styles.mapTabIcon}></span>
              Map View
            </button>
            <button
              className={`${styles.tabButton} ${activeTab === "stats" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("stats")}
            >
              <span className={styles.statsTabIcon}></span>
              Statistics
            </button>
            <button
              className={`${styles.tabButton} ${activeTab === "images" ? styles.activeTab : ""}`}
              onClick={() => setActiveTab("images")}
            >
              <span className={styles.imagesTabIcon}></span>
              Images
            </button>
          </div>
        </div>

        <div className={styles.dashboardContent}>
          {/* Map Tab */}
          <div className={`${styles.tabContent} ${activeTab === "map" ? styles.activeTabContent : ""}`}>
            <div className={styles.mapContainer} ref={mapContainerRef}>
              <GoogleMap
                mapContainerStyle={mapContainerStyle}
                onLoad={handleMapLoad}
                options={{
                  mapTypeControl: false,
                  fullscreenControl: true,
                  streetViewControl: false,
                  zoomControl: true,
                  styles: [
                    {
                      featureType: "all",
                      elementType: "labels.text.fill",
                      stylers: [{ color: "#2c3e50" }],
                    },
                    {
                      featureType: "water",
                      elementType: "geometry.fill",
                      stylers: [{ color: "#d1e5f2" }],
                    },
                    {
                      featureType: "administrative",
                      elementType: "geometry.stroke",
                      stylers: [{ color: "#cfd8dc" }],
                    },
                    {
                      featureType: "road",
                      elementType: "geometry",
                      stylers: [{ color: "#ffffff" }],
                    },
                    {
                      featureType: "poi",
                      elementType: "geometry",
                      stylers: [{ color: "#e8f5e9" }],
                    },
                  ],
                }}
              >
                {directionsResponse && (
                  <DirectionsRenderer
                    directions={directionsResponse}
                    options={{
                      suppressMarkers: true,
                      polylineOptions: {
                        strokeColor: "#3498db",
                        strokeOpacity: 0.8,
                        strokeWeight: 5,
                      },
                    }}
                  />
                )}
              </GoogleMap>
            </div>
          </div>

          {/* Stats Tab */}
          <div className={`${styles.tabContent} ${activeTab === "stats" ? styles.activeTabContent : ""}`}>
            <div className={styles.statsGrid}>
              <div className={styles.statCard}>
                <div className={styles.statIcon}></div>
                <div className={styles.statInfo}>
                  <h3>First Detection</h3>
                  <p>
                    {detectionResults.detections.length > 0
                      ? new Date(detectionResults.detections[0].timestamp).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statIcon}></div>
                <div className={styles.statInfo}>
                  <h3>Last Detection</h3>
                  <p>
                    {detectionResults.detections.length > 0
                      ? new Date(
                          detectionResults.detections[detectionResults.detections.length - 1].timestamp,
                        ).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statIcon}></div>
                <div className={styles.statInfo}>
                  <h3>Unique Locations</h3>
                  <p>{new Set(detectionResults.detections.map((d) => d.location)).size}</p>
                </div>
              </div>

              <div className={styles.statCard}>
                <div className={styles.statIcon}></div>
                <div className={styles.statInfo}>
                  <h3>Average Speed</h3>
                  <p>
                    {speedData.length > 0
                      ? Math.round(speedData.reduce((sum, d) => sum + d.speed, 0) / speedData.length) + ' km/h'
                      : 'N/A'}
                  </p>
                </div>
              </div>
            </div>

            <div className={styles.chartContainer}>
              <h3>Detection Frequency by Date</h3>
              <div className={styles.chart}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={frequencyData}
                    margin={{
                      top: 20,
                      right: 30,
                      left: 20,
                      bottom: 60,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis 
                      dataKey="date" 
                      angle={-45} 
                      textAnchor="end"
                      height={60}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#fff', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                      }}
                      formatter={(value) => [`${value} detections`, 'Count']}
                    />
                    <Bar 
                      dataKey="count" 
                      fill="#3498db" 
                      name="Detections" 
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className={styles.chartContainer}>
              <h3>Time of Day Pattern</h3>
              <div className={styles.chart}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={timeOfDayData}
                    margin={{
                      top: 20,
                      right: 30,
                      left: 20,
                      bottom: 30,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis 
                      dataKey="hour" 
                      label={{ value: 'Hour of Day', position: 'insideBottomRight', offset: -5 }}
                      tick={{ fontSize: 12 }}
                      tickFormatter={(hour) => `${hour}:00`}
                    />
                    <YAxis 
                      label={{ value: 'Detections', angle: -90, position: 'insideLeft', offset: -5 }}
                      tick={{ fontSize: 12 }}
                    />
                    <Tooltip 
                      formatter={(value) => [`${value} detections`, 'Count']}
                      labelFormatter={(hour) => `${hour}:00 - ${hour + 1}:00`}
                      contentStyle={{ 
                        backgroundColor: '#fff', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                      }}
                    />
                    <Bar 
                      dataKey="count" 
                      fill="#9b59b6" 
                      name="Detections" 
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className={styles.chartContainer}>
              <h3>Top Detection Locations</h3>
              <div className={styles.chart}>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={locationData}
                      cx="50%"
                      cy="50%"
                      labelLine={true}
                      outerRadius={100}
                      innerRadius={60}
                      fill="#8884d8"
                      dataKey="value"
                      nameKey="name"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      paddingAngle={2}
                    >
                      {locationData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(value) => [`${value} detections`, 'Count']}
                      contentStyle={{ 
                        backgroundColor: '#fff', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                      }}
                    />
                    <Legend 
                      layout="horizontal" 
                      verticalAlign="bottom" 
                      align="center"
                      iconType="circle"
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {speedData.length > 0 && (
              <div className={styles.chartContainer}>
                <h3>Speed Analysis by Time of Day</h3>
                <div className={styles.chart}>
                  <ResponsiveContainer width="100%" height={300}>
                    <ScatterChart
                      margin={{
                        top: 20,
                        right: 30,
                        left: 20,
                        bottom: 30,
                      }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis 
                        type="number" 
                        dataKey="hour" 
                        name="Hour of Day" 
                        label={{ value: 'Hour of Day', position: 'insideBottomRight', offset: -5 }}
                        domain={[0, 23]}
                        tick={{ fontSize: 12 }}
                        tickFormatter={(hour) => `${hour}:00`}
                      />
                      <YAxis 
                        type="number" 
                        dataKey="speed" 
                        name="Speed (km/h)" 
                        label={{ value: 'Speed (km/h)', angle: -90, position: 'insideLeft', offset: -5 }}
                        tick={{ fontSize: 12 }}
                      />
                      <ZAxis type="number" dataKey="count" range={[60, 400]} />
                      <Tooltip 
                        formatter={(value, name) => {
                          if (name === 'Hour of Day') return [`${value}:00 - ${Number(value) + 1}:00`, name];
                          return [`${value} km/h`, name];
                        }}
                        contentStyle={{ 
                          backgroundColor: '#fff', 
                          border: '1px solid #e0e0e0',
                          borderRadius: '8px',
                          boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                        }}
                      />
                      <Scatter 
                        name="Speed" 
                        data={speedData} 
                        fill="#e74c3c" 
                        shape="circle"
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          {/* Images Tab */}
          <div className={`${styles.tabContent} ${activeTab === "images" ? styles.activeTabContent : ""}`}>
            <div className={styles.imagesGrid}>
              {detectionResults.detections.map((detection, index) => (
                <div key={index} className={styles.imageCard}>
                  <div className={styles.imagePlaceholder}>
                    <span className={styles.cameraIcon}></span>
                    <span>Vehicle Image</span>
                  </div>
                  <div className={styles.imageInfo}>
                    <p className={styles.imageTime}>{new Date(detection.timestamp).toLocaleString()}</p>
                    <p className={styles.imageLocation}>{detection.location}</p>
                    {detection.speed && (
                      <p className={styles.imageSpeed}>Speed: {detection.speed} km/h</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DetectionResults
