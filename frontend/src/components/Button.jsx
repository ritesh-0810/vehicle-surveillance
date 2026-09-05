"use client"

import styles from "./Button.module.css"

const Button = ({ children, type = "button", variant = "primary", onClick, disabled = false, fullWidth = false }) => {
  return (
    <button
      type={type}
      className={`${styles.button} ${styles[variant]} ${fullWidth ? styles.fullWidth : ""}`}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  )
}

export default Button

