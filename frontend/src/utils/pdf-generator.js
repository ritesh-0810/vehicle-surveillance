import { jsPDF } from "jspdf"
import html2canvas from "html2canvas"

export async function generateDetectionReport(detectionResults, mapElement) {
  if (!detectionResults) return null

  try {
    const pdf = new jsPDF("p", "mm", "a4")

    // Add title and header
    pdf.setFontSize(22)
    pdf.setTextColor(33, 33, 33)
    pdf.text("Vehicle Detection Report", 105, 20, { align: "center" })

    // Add license plate info
    pdf.setFontSize(16)
    pdf.text(`License Plate: ${detectionResults.licensePlate}`, 20, 35)

    // Add date and metadata
    pdf.setFontSize(11)
    pdf.setTextColor(100, 100, 100)
    pdf.text(`Report Generated: ${new Date().toLocaleString()}`, 20, 45)
    pdf.text(`Total Detections: ${detectionResults.detections.length}`, 20, 52)

    // Add map screenshot if available
    if (mapElement) {
      try {
        pdf.text("Detection Map:", 20, 62)

        const mapCanvas = await html2canvas(mapElement, {
          useCORS: true,
          allowTaint: true,
          logging: false,
          scale: 2,
        })

        const mapImage = mapCanvas.toDataURL("image/png")
        pdf.addImage(mapImage, "PNG", 20, 65, 170, 80)
      } catch (mapError) {
        console.error("Error capturing map:", mapError)
        pdf.text("Map image could not be generated", 20, 70)
      }
    }

    // Add detection details
    pdf.setTextColor(33, 33, 33)
    pdf.setFontSize(14)
    pdf.text("Detection Details:", 20, 155)

    let yPosition = 165

    // Add each detection
    detectionResults.detections.forEach((detection, index) => {
      // Check if we need a new page
      if (yPosition > 250) {
        pdf.addPage()
        yPosition = 20
      }

      // Detection header
      pdf.setFontSize(12)
      pdf.setTextColor(33, 33, 33)
      pdf.text(`Detection #${index + 1}`, 20, yPosition)

      // Detection details
      pdf.setFontSize(10)
      pdf.setTextColor(80, 80, 80)
      pdf.text(`Time: ${new Date(detection.timestamp).toLocaleString()}`, 25, yPosition + 7)
      pdf.text(`Location: ${detection.location}`, 25, yPosition + 14)

      // Coordinates
      const { lat, lng } = detection.coordinates
      pdf.text(`Coordinates: ${lat.toFixed(6)}, ${lng.toFixed(6)}`, 25, yPosition + 21)

      // Add detection image if available
      // In a real app, you would fetch and add the actual image
      // pdf.addImage(detection.imageUrl, 'JPEG', 25, yPosition + 25, 60, 40)

      yPosition += 50
    })

    // Add footer
    const pageCount = pdf.internal.getNumberOfPages()
    for (let i = 1; i <= pageCount; i++) {
      pdf.setPage(i)
      pdf.setFontSize(8)
      pdf.setTextColor(150, 150, 150)
      pdf.text(
        `Vehicle Surveillance System - Page ${i} of ${pageCount}`,
        pdf.internal.pageSize.getWidth() / 2,
        pdf.internal.pageSize.getHeight() - 10,
        { align: "center" },
      )
    }

    return pdf
  } catch (error) {
    console.error("Error generating PDF:", error)
    return null
  }
}

