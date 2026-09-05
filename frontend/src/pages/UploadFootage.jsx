"use client"

import { useState } from "react"
import Button from "../components/Button"
import LocationSearch from "../components/LocationSearch"
import styles from "./UploadFootage.module.css"
import { API_BASE_URL } from "../config"

const UploadFootage = () => {
  const [files, setFiles] = useState([])
  const [location, setLocation] = useState("")
  const [coordinates, setCoordinates] = useState({ lat: null, lng: null })
  const [timestamp, setTimestamp] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [progressMap, setProgressMap] = useState({})
  const [statusMap, setStatusMap] = useState({})
  const [message, setMessage] = useState({ text: "", type: "" })
  const [activeStep, setActiveStep] = useState(1)

  const handleLocationSelect = (selectedLocation) => {
    setLocation(selectedLocation.placeAddress)
    setCoordinates({
      lat: selectedLocation.lat || null,
      lng: selectedLocation.lon || null,
    })
  }

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files)
    const validTypes = ["video/mp4", "video/avi", "video/quicktime"]

    const filteredFiles = selectedFiles.filter((file) => validTypes.includes(file.type))

    if (filteredFiles.length > 0) {
      setFiles([...files, ...filteredFiles])
      setMessage({ text: "", type: "" })
    } else {
      setMessage({
        text: "Please select valid video files (.mp4, .avi, .mov)",
        type: "error",
      })
    }
  }

  const removeFile = (index) => {
    const newFiles = [...files]
    newFiles.splice(index, 1)
    setFiles(newFiles)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (files.length === 0) {
      setMessage({ text: "Please select at least one video file", type: "error" })
      return
    }

    if (!location || !coordinates.lat || !coordinates.lng) {
      setMessage({ text: "Please select a valid location", type: "error" })
      return
    }

    if (!timestamp) {
      setMessage({ text: "Please select a timestamp", type: "error" })
      return
    }

    setIsUploading(true)
    setMessage({ text: "Uploading videos...", type: "info" })

    try {
      for (const file of files) {
        await uploadSingleFile(file)
      }
    } catch (error) {
      console.error("Upload error:", error)
    } finally {
      setIsUploading(false)
    }
  }

  const uploadSingleFile = async (file) => {
    setProgressMap((prev) => ({ ...prev, [file.name]: 0 }))
    setStatusMap((prev) => ({ ...prev, [file.name]: "Uploading..." }))

    try {
      const formData = new FormData()
      formData.append("video", file)
      formData.append("location", location)
      formData.append("latitude", coordinates.lat)
      formData.append("longitude", coordinates.lng)
      formData.append("timestamp", timestamp)

      const response = await fetch(`${API_BASE_URL}/process`, {
        method: "POST",
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`)
      }

      const result = await response.json()
      console.log(`✅ Uploaded ${file.name}:`, result)

      setStatusMap((prev) => ({ ...prev, [file.name]: "Processing..." }))
      setProgressMap((prev) => ({ ...prev, [file.name]: 5 }))

      pollProgress(result.session_id, file.name)
    } catch (error) {
      console.error(`❌ Upload Error (${file.name}):`, error)
      setStatusMap((prev) => ({ ...prev, [file.name]: "Error" }))
      setMessage({ text: `Upload failed for ${file.name}: ${error.message}`, type: "error" })
    }
  }

  const pollProgress = (sessionId, fileName) => {
    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/status/${sessionId}`)
        if (!response.ok) throw new Error("Failed to fetch progress")

        const data = await response.json()
        setProgressMap((prev) => ({ ...prev, [fileName]: data.progress }))
        setStatusMap((prev) => ({ ...prev, [fileName]: data.status }))

        if (data.progress >= 100) {
          clearInterval(interval)
          setMessage({ text: `Processing complete for ${fileName}!`, type: "success" })
        }
      } catch (error) {
        console.error(`❌ Progress Fetch Error (${fileName}):`, error)
        setStatusMap((prev) => ({ ...prev, [fileName]: "Error fetching progress" }))
        clearInterval(interval)
      }
    }, 2000)
  }

  const nextStep = () => {
    if (activeStep === 1 && files.length === 0) {
      setMessage({ text: "Please select at least one video file", type: "error" })
      return
    }

    if (activeStep === 2 && (!location || !coordinates.lat || !coordinates.lng)) {
      setMessage({ text: "Please select a valid location", type: "error" })
      return
    }

    setActiveStep((prev) => prev + 1)
    setMessage({ text: "", type: "" })
  }

  const prevStep = () => {
    setActiveStep((prev) => prev - 1)
    setMessage({ text: "", type: "" })
  }

  return (
    <div className={styles.pageContainer}>
      <div className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <div className={styles.logoIcon}></div>
          <h1>Upload Footage</h1>
        </div>

        <div className={styles.stepsList}>
          <div
            className={`${styles.stepItem} ${activeStep === 1 ? styles.active : ""} ${activeStep > 1 ? styles.completed : ""}`}
          >
            <div className={styles.stepNumber}>1</div>
            <div className={styles.stepText}>
              <h3>Select Files</h3>
              <p>Choose video files to upload</p>
            </div>
          </div>

          <div
            className={`${styles.stepItem} ${activeStep === 2 ? styles.active : ""} ${activeStep > 2 ? styles.completed : ""}`}
          >
            <div className={styles.stepNumber}>2</div>
            <div className={styles.stepText}>
              <h3>Location</h3>
              <p>Specify where footage was captured</p>
            </div>
          </div>

          <div
            className={`${styles.stepItem} ${activeStep === 3 ? styles.active : ""} ${activeStep > 3 ? styles.completed : ""}`}
          >
            <div className={styles.stepNumber}>3</div>
            <div className={styles.stepText}>
              <h3>Timestamp</h3>
              <p>Set date and time of recording</p>
            </div>
          </div>

          <div className={`${styles.stepItem} ${activeStep === 4 ? styles.active : ""}`}>
            <div className={styles.stepNumber}>4</div>
            <div className={styles.stepText}>
              <h3>Upload</h3>
              <p>Process and analyze footage</p>
            </div>
          </div>
        </div>

        <div className={styles.sidebarFooter}>
          <div className={styles.helpIcon}></div>
          <p>Need help? Contact support</p>
        </div>
      </div>

      <div className={styles.mainContent}>
        {message.text && <div className={`${styles.message} ${styles[message.type]}`}>{message.text}</div>}

        <form onSubmit={handleSubmit} className={styles.form}>
          {/* Step 1: Select Files */}
          <div className={`${styles.step} ${activeStep === 1 ? styles.activeStep : ""}`}>
            <div className={styles.stepHeader}>
              <h2>Select Video Files</h2>
              <p>Choose surveillance footage files to upload for analysis</p>
            </div>

            <div className={styles.fileUpload}>
              <label htmlFor="video-upload" className={styles.fileInfo}>
                <div className={styles.uploadIconWrapper}>
                  <div className={styles.uploadIcon}></div>
                </div>
                <span>Click to select files or drag and drop</span>
                <span className={styles.supportedFormats}>Supports .mp4, .avi, .mov</span>
                <input
                  type="file"
                  id="video-upload"
                  accept=".mp4,.avi,.mov"
                  onChange={handleFileChange}
                  multiple
                  className={styles.fileInput}
                  disabled={isUploading}
                />
              </label>
            </div>

            {files.length > 0 && (
              <div className={styles.fileListWrapper}>
                <div className={styles.fileListHeader}>
                  <span>Selected Files ({files.length})</span>
                </div>
                <ul className={styles.fileList}>
                  {files.map((file, index) => (
                    <li key={index}>
                      <div className={styles.fileDetails}>
                        <div className={styles.fileIcon}></div>
                        <div className={styles.fileInfo}>
                          <span className={styles.fileName}>{file.name}</span>
                          <span className={styles.fileSize}>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeFile(index)}
                        className={styles.removeButton}
                        disabled={isUploading}
                        aria-label="Remove file"
                      >
                        ×
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className={styles.stepActions}>
              <Button type="button" onClick={nextStep} disabled={isUploading}>
                Continue to Location
              </Button>
            </div>
          </div>

          {/* Step 2: Location */}
          <div className={`${styles.step} ${activeStep === 2 ? styles.activeStep : ""}`}>
            <div className={styles.stepHeader}>
              <h2>Specify Location</h2>
              <p>Enter the location where the footage was captured</p>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="location">Search for a location</label>
              <LocationSearch onLocationSelect={handleLocationSelect} />
              {coordinates.lat && coordinates.lng && (
                <div className={styles.coordinates}>
                  <span className={styles.coordinatesIcon}></span>
                  {coordinates.lat.toFixed(6)}, {coordinates.lng.toFixed(6)}
                </div>
              )}
            </div>

            <div className={styles.stepActions}>
              <Button type="button" variant="outline" onClick={prevStep} disabled={isUploading}>
                Back
              </Button>
              <Button type="button" onClick={nextStep} disabled={isUploading}>
                Continue to Timestamp
              </Button>
            </div>
          </div>

          {/* Step 3: Timestamp */}
          <div className={`${styles.step} ${activeStep === 3 ? styles.activeStep : ""}`}>
            <div className={styles.stepHeader}>
              <h2>Set Timestamp</h2>
              <p>Specify when the footage was recorded</p>
            </div>

            <div className={styles.formGroup}>
              <label htmlFor="timestamp">Date and Time</label>
              <div className={styles.inputWrapper}>
                <input
                  type="datetime-local"
                  id="timestamp"
                  value={timestamp}
                  onChange={(e) => setTimestamp(e.target.value)}
                  className={styles.input}
                  required
                  disabled={isUploading}
                />
                <div className={styles.calendarIcon}></div>
              </div>
            </div>

            <div className={styles.stepActions}>
              <Button type="button" variant="outline" onClick={prevStep} disabled={isUploading}>
                Back
              </Button>
              <Button type="button" onClick={nextStep} disabled={isUploading}>
                Continue to Upload
              </Button>
            </div>
          </div>

          {/* Step 4: Upload */}
          <div className={`${styles.step} ${activeStep === 4 ? styles.activeStep : ""}`}>
            <div className={styles.stepHeader}>
              <h2>Upload and Process</h2>
              <p>Start the upload and processing of your footage</p>
            </div>

            <div className={styles.uploadSummary}>
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Files:</span>
                <span className={styles.summaryValue}>{files.length} video files selected</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Location:</span>
                <span className={styles.summaryValue}>{location || "Not specified"}</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Timestamp:</span>
                <span className={styles.summaryValue}>{timestamp || "Not specified"}</span>
              </div>
            </div>

            <div className={styles.stepActions}>
              <Button type="button" variant="outline" onClick={prevStep} disabled={isUploading}>
                Back
              </Button>
              <Button type="submit" disabled={isUploading}>
                {isUploading ? (
                  <span className={styles.loadingWrapper}>
                    <span className={styles.loadingDot}></span>
                    <span className={styles.loadingDot}></span>
                    <span className={styles.loadingDot}></span>
                    <span>Uploading</span>
                  </span>
                ) : (
                  <span className={styles.buttonContent}>Start Upload</span>
                )}
              </Button>
            </div>
          </div>
        </form>

        {Object.keys(progressMap).length > 0 && (
          <div className={styles.progressSection}>
            <h2>Upload Progress</h2>
            <div className={styles.progressGrid}>
              {files.map((file, index) => (
                <div key={index} className={styles.progressContainer}>
                  <div className={styles.progressHeader}>
                    <div className={styles.progressFileInfo}>
                      <div className={styles.fileIcon}></div>
                      <h3>{file.name}</h3>
                    </div>
                    <span
                      className={styles.status}
                      data-status={statusMap[file.name]?.replace(/\.\.\./g, "").toLowerCase() || "waiting"}
                    >
                      {statusMap[file.name] || "Waiting..."}
                    </span>
                  </div>
                  <div className={styles.progressBarWrapper}>
                    <div className={styles.progressBar} style={{ width: `${progressMap[file.name] || 0}%` }}></div>
                  </div>
                  <div className={styles.progressPercentage}>{progressMap[file.name] || 0}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default UploadFootage
