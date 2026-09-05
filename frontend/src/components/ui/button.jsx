// src/components/ui/button.jsx
import React from "react"

export function Button({ children, variant = "default", className = "", ...props }) {
  const baseClasses = "px-4 py-2 rounded-md font-medium transition-colors"
  const variantClasses = {
    default: "bg-primary text-primary-foreground hover:bg-primary/90",
    outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
    ghost: "hover:bg-accent hover:text-accent-foreground",
  }

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}