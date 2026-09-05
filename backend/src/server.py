# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import os
import uuid
import socket
import logging
from logging.handlers import RotatingFileHandler
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.serving import run_simple
import threading
import traceback
import sys
import time
from functools import wraps
import re
import shutil
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    logger.critical("MONGODB_URI environment variable is not set")
    sys.exit(1)

# Connect to MongoDB
try:
    client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    # Verify connection
    client.server_info()
    logger.info("Successfully connected to MongoDB")
    db = client["number_plate_db"]
    sessions_collection = db["sessions"]
    results_collection = db["plate_detections"]
except Exception as e:
    logger.critical(f"Failed to connect to MongoDB: {str(e)}")
    sys.exit(1)

app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = os.path.abspath("uploads")
PROCESSED_FOLDER = os.path.abspath("processed_data")
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB max upload size
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Rate limiting decorator
def rate_limit(limit=10, window=60):
    """Basic rate limiting decorator"""
    ips = {}
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr
            now = time.time()
            
            # Clean old entries
            ips_to_remove = []
            for stored_ip, requests in ips.items():
                ips[stored_ip] = [req for req in requests if now - req < window]
                if not ips[stored_ip]:
                    ips_to_remove.append(stored_ip)
            
            for ip_to_remove in ips_to_remove:
                del ips[ip_to_remove]
            
            # Check rate limit
            if ip in ips and len(ips[ip]) >= limit:
                return jsonify({"error": "Rate limit exceeded"}), 429
            
            # Add new request timestamp
            if ip not in ips:
                ips[ip] = []
            ips[ip].append(now)
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

# Request validation
def validate_video_request():
    """Validate video upload request"""
    if "video" not in request.files:
        return {"error": "No video file provided"}, 400
    
    video = request.files["video"]
    if video.filename == '':
        return {"error": "Empty video filename"}, 400
    
    # Check file extension
    allowed_extensions = {'mp4', 'avi', 'mov', 'mkv', 'webm'}
    if '.' not in video.filename or video.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        return {"error": "Invalid video format. Allowed formats: mp4, avi, mov, mkv, webm"}, 400
    
    return None

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    # Replace dangerous characters
    return re.sub(r'[^\w\.-]', '_', filename)

def sanitize_input(text):
    """Basic input sanitization"""
    if text is None:
        return None
    return re.sub(r'[;<>&\'"\\]', '_', str(text))

@app.route("/", methods=["GET"])
def index():
    return "[OK] Flask server is running."

@app.route("/test-process", methods=["GET"])
@rate_limit(limit=5, window=60)
def test_process():
    return jsonify({"message": "[OK] /process endpoint is alive!"})

@app.route("/net-test")
@rate_limit(limit=5, window=60)
def net_test():
    try:
        ipv4 = socket.gethostbyname('localhost')
        ipv6_info = socket.getaddrinfo('localhost', 5001, socket.AF_INET6)
        ipv6 = ipv6_info[0][4][0] if ipv6_info else "No IPv6 address"
        return jsonify({
            "ipv4": ipv4,
            "ipv6": ipv6,
            "hostname": socket.gethostname(),
            "active_connections": str(socket.getaddrinfo(socket.gethostname(), 5001))
        })
    except Exception as e:
        logger.error(f"Network test failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/search-location", methods=["GET"])
@rate_limit(limit=30, window=60)
def search_location():
    """Search for locations via OpenStreetMap Nominatim & DB session records"""
    query = request.args.get("q", "").strip()
    
    if not query:
        return jsonify({"query": "", "suggestedLocations": [], "count": 0})
    
    query = sanitize_input(query)
    suggested_locations = []
    seen_addresses = set()
    
    # 1. Geocode search via OpenStreetMap Nominatim
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "VehicleSurveillanceApp/1.0"}
        params = {"q": query, "format": "json", "addressdetails": 1, "limit": 5}
        resp = requests.get(url, headers=headers, params=params, timeout=4)
        if resp.ok:
            for item in resp.json():
                display_name = item.get("display_name", "")
                parts = display_name.split(",")
                place_name = parts[0].strip() if parts else query
                lat = float(item["lat"]) if "lat" in item else None
                lon = float(item["lon"]) if "lon" in item else None
                
                if display_name not in seen_addresses:
                    seen_addresses.add(display_name)
                    suggested_locations.append({
                        "placeName": place_name,
                        "placeAddress": display_name,
                        "latitude": lat,
                        "longitude": lon,
                        "placeId": str(item.get("place_id", uuid.uuid4()))
                    })
    except Exception as e:
        logger.warning(f"Nominatim geocoding failed: {str(e)}")

    # 2. Database search in local sessions collection
    try:
        sessions_cursor = sessions_collection.find({
            "location": {"$regex": query, "$options": "i"}
        }).limit(5)
        
        for session in sessions_cursor:
            loc_name = session.get("location", "").strip()
            if loc_name and loc_name not in seen_addresses:
                seen_addresses.add(loc_name)
                lat_val = session.get("latitude")
                lng_val = session.get("longitude")
                suggested_locations.append({
                    "placeName": loc_name.split(",")[0].strip(),
                    "placeAddress": loc_name,
                    "latitude": float(lat_val) if lat_val is not None else None,
                    "longitude": float(lng_val) if lng_val is not None else None,
                    "placeId": str(session.get("session_id", uuid.uuid4()))
                })
    except Exception as e:
        logger.warning(f"Database location search failed: {str(e)}")

    return jsonify({
        "query": query,
        "suggestedLocations": suggested_locations,
        "count": len(suggested_locations)
    })

def run_processing_pipeline(video_path, plates_output_folder, session_id):
    """Run the video processing pipeline in a separate thread"""
    try:
        # Update status to indicate processing has started
        sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": "Processing started", "progress": 10}}
        )

        # Get absolute paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        recognition_script = os.path.join(current_dir, "plate_recognition.py")
        extraction_script = os.path.join(current_dir, "extract_unique_plates.py")

        # Normalize paths
        video_path = os.path.normpath(video_path)
        plates_output_folder = os.path.normpath(plates_output_folder)
        recognition_script = os.path.normpath(recognition_script)
        extraction_script = os.path.normpath(extraction_script)

        # Get the absolute Python interpreter path
        python_executable = sys.executable

        logger.info(f"Running plate_recognition.py for session {session_id}...")
        logger.info(f"Using Python executable: {python_executable}")
        logger.info(f"Recognition script path: {recognition_script}")
        logger.info(f"Command: {python_executable} \"{recognition_script}\" \"{video_path}\" \"{plates_output_folder}\" {session_id}")

        try:
            # MODIFIED: Remove Windows-specific flags and use more compatible approach
            process = subprocess.Popen(
                [python_executable, recognition_script, video_path, plates_output_folder, session_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=current_dir,  # Run from the script's directory
                env=os.environ.copy()  # Use a copy of the current environment
            )
            
            # Stream output in real-time with timeout
            stdout, stderr = process.communicate(timeout=300)  # 5-minute timeout
            
            if process.returncode == 0:
                logger.info(f"plate_recognition.py completed for session {session_id}.")
                logger.info(f"Output: {stdout}")
                if stderr:
                    logger.warning(f"Stderr: {stderr}")
                
                sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": "Plate recognition complete", "progress": 50}}
                )
            else:
                logger.error(f"plate_recognition.py failed with return code {process.returncode}")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                
                sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": f"Recognition Error: Process returned {process.returncode}", "progress": 25}}
                )

            # Check if plates were actually generated
            if not os.path.exists(plates_output_folder) or len(os.listdir(plates_output_folder)) == 0:
                logger.warning(f"No plates were generated in {plates_output_folder}")
                sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": "Warning: No plates detected", "progress": 60}}
                )

        except subprocess.TimeoutExpired:
            logger.error(f"plate_recognition.py timed out after 300 seconds")
            process.kill()
            sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"status": "Recognition Error: Process timed out", "progress": 25}}
            )
        except Exception as e:
            logger.error(f"plate_recognition.py exception: {str(e)}")
            logger.error(traceback.format_exc())
            sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"status": f"Recognition Error: {str(e)}", "progress": 25}}
            )

        # Always proceed to extraction step
        logger.info(f"Running extract_unique_plates.py for session {session_id}...")
        logger.info(f"Extraction script path: {extraction_script}")
        logger.info(f"Command: {python_executable} \"{extraction_script}\" {session_id}")

        try:
            # Update status to show extraction is starting
            sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"status": "Extracting license plates...", "progress": 60}}
            )
            
            # Use a more robust subprocess approach
            extraction_command = [python_executable, extraction_script, session_id, plates_output_folder]
            logger.info(f"Executing extraction command: {' '.join(extraction_command)}")
            
            # Start the process with proper environment
            env = os.environ.copy()
            env['PYTHONPATH'] = current_dir
            
            process = subprocess.Popen(
                extraction_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout
                text=True,
                cwd=current_dir,
                env=env,
                bufsize=0,  # Unbuffered
                universal_newlines=True
            )
            
            # Read output in real-time and update progress
            output_lines = []
            start_time = time.time()
            timeout_seconds = 900  # 15 minutes
            
            logger.info("Starting real-time output monitoring...")
            
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    # Process has completed
                    remaining_output = process.stdout.read()
                    if remaining_output:
                        output_lines.append(remaining_output)
                        logger.info(f"Final output: {remaining_output}")
                    break
                
                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    logger.error(f"Extraction process timed out after {timeout_seconds} seconds")
                    process.kill()
                    sessions_collection.update_one(
                        {"session_id": session_id},
                        {"$set": {"status": "Extraction Error: Process timed out", "progress": 75}}
                    )
                    return
                
                # Try to read a line (non-blocking)
                try:
                    line = process.stdout.readline()
                    if line:
                        output_lines.append(line.strip())
                        logger.info(f"Extraction output: {line.strip()}")
                        
                        # Update progress based on output
                        if "Progress:" in line and "%" in line:
                            try:
                                # Extract percentage from progress line
                                percent_str = line.split("%")[0].split()[-1]
                                progress = int(float(percent_str))
                                # Map extraction progress to 60-95% of total progress
                                total_progress = 60 + int((progress / 100) * 35)
                                sessions_collection.update_one(
                                    {"session_id": session_id},
                                    {"$set": {"status": f"Extracting license plates... {progress}%", "progress": total_progress}}
                                )
                            except:
                                pass
                                
                except:
                    # No more output available, continue waiting
                    time.sleep(0.1)
                    continue
            
            # Process completed
            return_code = process.returncode
            logger.info(f"Extraction process completed with return code: {return_code}")
            
            if return_code == 0:
                logger.info(f"extract_unique_plates.py completed successfully for session {session_id}")
                
                # Final success update
                sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": "Processing complete", "progress": 100}}
                )
                
                # Log summary of results
                for line in output_lines:
                    if "unique plates found" in line:
                        logger.info(f"Extraction results: {line}")
                    elif "Processing time:" in line:
                        logger.info(f"Extraction performance: {line}")
                        
            else:
                logger.error(f"extract_unique_plates.py failed with return code {return_code}")
                error_output = "\n".join(output_lines[-10:])  # Last 10 lines for error context
                logger.error(f"Last output: {error_output}")
                
                sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": {"status": f"Extraction Error: Process returned {return_code}", "progress": 75}}
                )
                
        except Exception as e:
            logger.error(f"extract_unique_plates.py exception: {str(e)}")
            logger.error(traceback.format_exc())
            sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"status": f"Extraction Error: {str(e)}", "progress": 75}}
            )

    except Exception as e:
        logger.error(f"General pipeline error: {str(e)}")
        logger.error(traceback.format_exc())
        sessions_collection.update_one(
            {"session_id": session_id},
            {"$set": {"status": f"Pipeline Error: {str(e)}", "progress": 30}}
        )

@app.route("/process", methods=["POST"])
@rate_limit(limit=5, window=300)  # Limit to 5 requests per 5 minutes
def process_video():
    # Validate the request
    validation_error = validate_video_request()
    if validation_error:
        return jsonify(validation_error[0]), validation_error[1]

    video = request.files["video"]
    # Sanitize inputs
    location = sanitize_input(request.form.get("location", "Unknown Location"))
    latitude = sanitize_input(request.form.get("latitude", None))
    longitude = sanitize_input(request.form.get("longitude", None))
    timestamp = sanitize_input(request.form.get("timestamp", "Unknown Timestamp"))

    session_id = str(uuid.uuid4())
    safe_filename = sanitize_filename(video.filename)
    video_filename = f"{session_id}_{safe_filename}"
    video_path = os.path.join(UPLOAD_FOLDER, video_filename)
    
    try:
        video.save(video_path)
    except Exception as e:
        logger.error(f"Failed to save video: {str(e)}")
        return jsonify({"error": "Failed to save video file"}), 500

    # Create session folder structure
    session_folder = os.path.join(PROCESSED_FOLDER, session_id)
    plates_output_folder = os.path.join(session_folder, "plates")
    video_output_folder = os.path.join(session_folder, "video_output")

    # Ensure directories exist
    try:
        os.makedirs(session_folder, exist_ok=True)
        os.makedirs(plates_output_folder, exist_ok=True)
        os.makedirs(video_output_folder, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create session directories: {str(e)}")
        return jsonify({"error": "Failed to create processing directories"}), 500

    logger.info(f"Created session folder structure:")
    logger.info(f"   - Session folder: {session_folder}")
    logger.info(f"   - Plates folder: {plates_output_folder}")
    logger.info(f"   - Video output folder: {video_output_folder}")

    # Convert latitude/longitude to float if possible
    try:
        if latitude is not None:
            latitude = float(latitude)
        if longitude is not None:
            longitude = float(longitude)
    except ValueError:
        latitude = None
        longitude = None
        logger.warning(f"Invalid latitude/longitude format for session {session_id}")

    metadata = {
        "session_id": session_id,
        "video_filename": video_filename,
        "location": location,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
        "status": "Waiting...",
        "progress": 0,
        "plates_folder": plates_output_folder,
        "video_output": video_output_folder,
        "created_at": time.time()
    }

    try:
        sessions_collection.insert_one(metadata)
        logger.info(f"Inserted session metadata into MongoDB with session_id: {session_id}")
    except Exception as e:
        logger.error(f"Failed to insert session metadata: {str(e)}")
        return jsonify({"error": "Database operation failed"}), 500

    # Start processing in a separate thread to avoid blocking the response
    processing_thread = threading.Thread(
        target=run_processing_pipeline,
        args=(video_path, plates_output_folder, session_id)
    )
    processing_thread.daemon = True  # Make thread a daemon so it doesn't block server shutdown
    processing_thread.start()

    return jsonify({
        "message": "Video received. Processing started.",
        "session_id": session_id,
        "video_path": video_path,
        "location": location,
        "timestamp": timestamp,
        "plates_folder": plates_output_folder,
        "video_output": video_output_folder
    }), 202

@app.route("/status/<session_id>", methods=["GET"])
def get_status(session_id):
    # Validate session_id format
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', session_id):
        return jsonify({"error": "Invalid session ID format"}), 400
        
    try:
        session = sessions_collection.find_one({"session_id": session_id})
        if not session:
            return jsonify({"status": "Not found", "progress": 0}), 404
        # Convert ObjectId to string for JSON serialization
        session["_id"] = str(session["_id"])
        return jsonify(session)
    except Exception as e:
        logger.error(f"Error retrieving session status: {str(e)}")
        return jsonify({"error": "Database operation failed"}), 500

@app.route("/plates/<session_id>", methods=["GET"])
def get_plate_results(session_id):
    # Validate session_id format
    if not re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', session_id):
        return jsonify({"error": "Invalid session ID format"}), 400
        
    try:
        results_cursor = results_collection.find({"session_id": session_id})
        results = []
        for doc in results_cursor:
            doc["_id"] = str(doc["_id"])  # Prevent serialization error
            results.append(doc)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error retrieving plate results: {str(e)}")
        return jsonify({"error": "Database operation failed"}), 500

@app.route("/status/all", methods=["GET"])
@rate_limit(limit=10, window=60)  # Limit to 10 requests per minute
def get_all_sessions():
    try:
        # Add pagination support
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Limit per_page to reasonable values
        per_page = min(per_page, 100)
        
        # Calculate skip value
        skip = (page - 1) * per_page
        
        # Get total count
        total_count = sessions_collection.count_documents({})
        
        # Get paginated results, sorted by creation time
        sessions_cursor = sessions_collection.find({}).sort("created_at", -1).skip(skip).limit(per_page)
        
        sessions = []
        for session in sessions_cursor:
            session["_id"] = str(session["_id"])  # Prevent serialization error
            sessions.append(session)
            
        return jsonify({
            "sessions": sessions,
            "page": page,
            "per_page": per_page,
            "total_count": total_count,
            "total_pages": (total_count + per_page - 1) // per_page
        })
    except Exception as e:
        logger.error(f"Error retrieving all sessions: {str(e)}")
        return jsonify({"error": "Database operation failed"}), 500

@app.route("/search", methods=["GET"])
@rate_limit(limit=20, window=60)  # Limit to 20 requests per minute
def search_by_plate():
    plate_number = request.args.get("plate", "").strip().upper()
    if not plate_number:
        return jsonify({"error": "Plate number is required"}), 400

    # Validate plate number format
    if not re.match(r'^[A-Z0-9\s-]{1,15}$', plate_number):
        return jsonify({"error": "Invalid plate number format"}), 400

    logger.info(f"Incoming plate search: '{plate_number}'")

    try:
        # Use regex to match plate numbers, ignoring whitespace and case
        pattern = re.compile(r'^\s*' + re.escape(plate_number) + r'\s*$', re.IGNORECASE)
        matches = list(results_collection.find({
            "plate_number": pattern
        }))

        logger.info(f"Matches found: {len(matches)}")

        results = []
        for m in matches:
            coords = {"lat": None, "lng": None}
            lat_raw = m.get("latitude", "")
            lng_raw = m.get("longitude", "")

            try:
                lat = float(lat_raw) if lat_raw else None
                lng = float(lng_raw) if lng_raw else None
                if lat is not None and lng is not None:
                    coords = {"lat": lat, "lng": lng}
            except (ValueError, TypeError):
                logger.warning(f"Invalid lat/lng for plate {m.get('plate_number')}")

            results.append({
                "plate": m.get("plate_number"),
                "timestamp": m.get("timestamp"),
                "location": m.get("location"),
                "image_path": m.get("image_path"),
                "coordinates": coords,
                "_id": str(m["_id"])  # Fix for serialization
            })

        logger.info(f"Results sent to frontend: {len(results)} items")
        return jsonify(results)

    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/image/<path:filename>", methods=["GET"])
def serve_image(filename):
    """Serve stored images"""
    # Sanitize the filename to prevent path traversal
    filename = sanitize_filename(filename)
    
    # Determine the directory based on the file path
    if filename.startswith("processed_data"):
        # Strip the leading "processed_data/" if present
        path = os.path.normpath(filename)
        directory = os.path.dirname(path)
        base_filename = os.path.basename(path)
        return send_from_directory(directory, base_filename)
    else:
        return jsonify({"error": "Invalid file path"}), 400

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check MongoDB connection
        client.server_info()
        # Check disk space
        _, _, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "disk_space_gb": free_gb,
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({"error": "File too large. Maximum size is 100MB"}), 413

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    try:
        logger.info(f"Starting server on port {port}...")
        run_simple('127.0.0.1', port, app, threaded=True, use_reloader=False)
    except Exception as e:
        logger.error(f"Server failed to start on port {port}: {str(e)}")
        try:
            logger.warning(f"Attempting fallback binding to 0.0.0.0:{port}...")
            app.run(host='0.0.0.0', port=port, threaded=True, debug=False, use_reloader=False)
        except Exception as e:
            logger.critical(f"Final startup failed: {str(e)}")
            sys.exit(1)