import { Link } from "react-router-dom"
import styles from "./Navbar.module.css"

const Navbar = () => {
  return (
    <div className={styles.navbarContainer}>
      <nav className={styles.navbar}>
        <div className={styles.logo}>
          <Link to="/">
            <span className={styles.logoIcon}></span>
            <span className={styles.logoText}>Vehicle Surveillance</span>
          </Link>
        </div>

        <div className={styles.navLinks}>
          {/* <Link to="/" className={styles.navLink}>
            <span className={styles.navIcon}></span>
            <span>Upload</span>
          </Link> */}

          <Link to="/search" className={styles.navLink}>
            <span className={styles.searchIcon}></span>
            <span>Search</span>
          </Link>
        </div>

        <div className={styles.userActions}>
          <button className={styles.actionButton}>
            <span className={styles.notificationIcon}></span>
          </button>
          <button className={styles.actionButton}>
            <span className={styles.settingsIcon}></span>
          </button>
          <div className={styles.userAvatar}></div>
        </div>
      </nav>
    </div>
  )
}

export default Navbar
