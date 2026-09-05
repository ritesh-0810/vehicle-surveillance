"use client"

import { useState } from "react"
import { BrowserRouter as Router, Routes, Route } from "react-router-dom"
import UploadFootage from "./pages/UploadFootage"
import SearchDetection from "./pages/SearchDetection"
import DetectionResults from "./pages/DetectionResults"
import Navbar from "./components/Navbar"
import "./App.css"

function App() {
  // We'll use this state to pass detection results between components
  const [detectionResults, setDetectionResults] = useState(null)

  return (
    <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <div className="app">
        <Navbar />
        <main className="content">
          <Routes>
            <Route path="/" element={<UploadFootage />} />
            <Route path="/search" element={<SearchDetection setDetectionResults={setDetectionResults} />} />
            <Route path="/results" element={<DetectionResults detectionResults={detectionResults} />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App