"use client"

import { useState } from "react"
import { useNavigate } from "react-router-dom"
import Button from "../components/Button"
import styles from "./SearchDetection.module.css"
import { API_BASE_URL } from "../config"

// Helper function to normalize license plate by removing whitespaces
const normalizeLicensePlate = (licensePlate) => {
  return licensePlate ? licensePlate.replace(/\s+/g, "").toUpperCase() : "";
}

const SearchDetection = ({ setDetectionResults }) => {
  const [licensePlate, setLicensePlate] = useState("")
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState("")
  const navigate = useNavigate()

  const handleSearch = async (e) => {
    e.preventDefault()
    setError("")

    if (!licensePlate.trim()) {
      setError("Please enter a license plate number")
      return
    }

    setIsSearching(true)

    try {
      // Normalize the license plate before searching
      const normalizedLicensePlate = normalizeLicensePlate(licensePlate)
      
      // Send the normalized license plate to the API
      const response = await fetch(`${API_BASE_URL}/search?plate=${normalizedLicensePlate}`)
      const data = await response.json()

      if (!response.ok) throw new Error(data.error || "Unknown error")

      if (data.length > 0) {
        // Store the original format for display, but ensure it's uppercase
        setDetectionResults({ 
          licensePlate: licensePlate.toUpperCase(), 
          normalizedLicensePlate: normalizedLicensePlate,
          detections: data 
        })
        navigate("/results")
      } else {
        setError("No detections found for this license plate.")
      }
    } catch (error) {
      setError(`Search failed: ${error.message}`)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className={styles.pageContainer}>
      <div className={styles.searchPanel}>
        <div className={styles.searchContent}>
          <div className={styles.searchHeader}>
            <div className={styles.headerIcon}></div>
            <h1>Search License Plate</h1>
          </div>

          <p className={styles.description}>
            Enter a license plate number to search for matches in the surveillance database.
          </p>

          {error && <div className={styles.error}>{error}</div>}

          <form onSubmit={handleSearch} className={styles.form}>
            <div className={styles.formGroup}>
              <label htmlFor="license-plate">License Plate Number</label>
              <div className={styles.inputWrapper}>
                <input
                  type="text"
                  id="license-plate"
                  value={licensePlate}
                  onChange={(e) => setLicensePlate(e.target.value)}
                  placeholder="Enter license plate (e.g., MH 12 AB 3246)"
                  className={styles.input}
                />
              </div>
            </div>

            <Button type="submit" disabled={isSearching} fullWidth>
              {isSearching ? (
                <span className={styles.loadingWrapper}>
                  <span className={styles.loadingDot}></span>
                  <span className={styles.loadingDot}></span>
                  <span className={styles.loadingDot}></span>
                  <span>Searching</span>
                </span>
              ) : (
                <span className={styles.buttonContent}>Search Database</span>
              )}
            </Button>
          </form>
        </div>
      </div>

      <div className={styles.infoPanel}>
        <div className={styles.infoContent}>
          <div className={styles.infoHeader}>
            <h2>Vehicle Surveillance System</h2>
          </div>

          <div className={styles.featureList}>
            <div className={styles.featureItem}>
              <div className={styles.featureIcon}></div>
              <div className={styles.featureText}>
                <h3>Real-time Detection</h3>
                <p>Track vehicles across multiple surveillance points</p>
              </div>
            </div>

            <div className={styles.featureItem}>
              <div className={styles.featureIcon}></div>
              <div className={styles.featureText}>
                <h3>Advanced Analytics</h3>
                <p>View movement patterns and generate detailed reports</p>
              </div>
            </div>

            <div className={styles.featureItem}>
              <div className={styles.featureIcon}></div>
              <div className={styles.featureText}>
                <h3>Secure Database</h3>
                <p>All vehicle data is securely stored and encrypted</p>
              </div>
            </div>
          </div>

          <div className={styles.recentSearches}>
            <h3>Recent Searches</h3>
            <div className={styles.searchList}>
              <div className={styles.searchItem}>
                <span className={styles.plateNumber}>ABC123</span>
                <span className={styles.searchTime}>Today, 10:45 AM</span>
              </div>
              <div className={styles.searchItem}>
                <span className={styles.plateNumber}>XYZ789</span>
                <span className={styles.searchTime}>Yesterday, 3:20 PM</span>
              </div>
              
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SearchDetection