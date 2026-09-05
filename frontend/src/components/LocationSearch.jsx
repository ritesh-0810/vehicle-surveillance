"use client"

import { useState, useEffect } from "react"
import styles from "./LocationSearch.module.css"
import { API_BASE_URL } from "../config"

const LocationSearch = ({ onLocationSelect }) => {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedPlace, setSelectedPlace] = useState(null)

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (query.trim()) {
        handleSearch()
      } else {
        setResults([])
        setError(null)
      }
    }, 500)

    return () => clearTimeout(debounceTimer)
  }, [query])

  const handleSearch = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 10000) // 10 second timeout
      
      const res = await fetch(`${API_BASE_URL}/api/search-location?q=${encodeURIComponent(query)}`, {
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`)
      }
      
      const data = await res.json()
      setResults(data.suggestedLocations || [])
      setSelectedPlace(null)
    } catch (error) {
      console.error("Search error:", error)
      if (error.name === 'AbortError') {
        setError("Search request timed out. Please try again.")
      } else {
        setError("Failed to search locations. Please check your connection.")
      }
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleSelectPlace = (result) => {
    setSelectedPlace(result)
    setQuery(result.placeName)
    setResults([])
    setError(null)

    if (onLocationSelect) {
      onLocationSelect({
        placeAddress: result.placeAddress,
        lat: result.latitude,
        lon: result.longitude,
        placeId: result.placeId,
      })
    }
  }

  return (
    <div className={styles.locationSearch}>
      <div className={styles.searchBox}>
        <span className={styles.searchIcon}></span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for a location"
          className={styles.searchInput}
        />
        {loading && <div className={styles.spinner}></div>}
      </div>

      {error && (
        <div className={styles.error}>
          {error}
        </div>
      )}

      {results.length > 0 && (
        <ul className={styles.suggestions}>
          {results.map((result, index) => (
            <li key={index} onClick={() => handleSelectPlace(result)}>
              <div className={styles.suggestionContent}>
                <span className={styles.locationPin}></span>
                <div className={styles.suggestionText}>
                  <strong>{result.placeName}</strong>
                  {result.placeAddress && <span>{result.placeAddress}</span>}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      {selectedPlace && !onLocationSelect && (
        <div className={styles.coordinates}>
          <h2>{selectedPlace.placeName}</h2>
          <p>{selectedPlace.placeAddress}</p>
          <div>
            <p>Coordinates:</p>
            <p>Latitude: {selectedPlace.latitude}</p>
            <p>Longitude: {selectedPlace.longitude}</p>
          </div>
        </div>
      )}
    </div>
  )
}

export default LocationSearch
