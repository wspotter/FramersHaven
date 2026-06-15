# Architecture & Codebase Details

This document explains the architecture of FramersHaven.

## Overview
FramersHaven is a **local-first** web application designed to run on a framing shop's workstation or trusted LAN. It avoids cloud dependencies so the shop can generate quotes and access history offline.

**Tech Stack:**
- **Backend:** Python, FastAPI
- **Database:** SQLite (local file)
- **Frontend:** Vanilla HTML/CSS/JavaScript (monolithic SPA design)
- **PDF Generation:** ReportLab
- **Image Processing:** Pillow (PIL), Cropper.js

## Directory Structure
- `app/main.py`: The core FastAPI application, routing, and business logic.
- `app/db.py` & `app/db_admin.py`: SQLite connection handling and table initialization.
- `app/pricing.py`: The quote calculation engine.
- `app/templates/index.html`: The monolithic Jinja2 template containing the entire Single Page Application (SPA) UI.
- `app/static/app.js`: The monolithic vanilla JavaScript file handling frontend state, UI updates, and API communication.
- `studio.db`, `uploads/`, `exports/`, `backups/`: Ignored local storage for the database, artwork, generated documents, and backups.

## Backend Architecture

### FastAPI & Routing
The backend is a single FastAPI app (`app = FastAPI()`). It serves:
1. REST API endpoints under `/api/*` for CRUD operations on quotes, customers, and catalog items.
2. Static files (CSS, JS, logos) and uploaded user artwork.
3. The root HTML template.

### Database (SQLite)
The app uses raw SQL queries via the standard `sqlite3` library. There is currently no ORM (like SQLAlchemy), keeping the footprint light and queries explicit.
Key tables include:
- `catalog_items`: Stores vendor mouldings, mats, and glazing.
- `service_options`: Stores shop-configurable labor/service charges (e.g., mounting, assembly).
- `orders` & `order_status_history`: Tracks saved quotes, work orders, and invoices.
- `customers`: Tracks customer details linked to orders.
- `images`: Tracks uploaded artwork metadata and crop dimensions.

### Quote Engine (`pricing.py`)
Pricing is calculated based on physical dimensions. 
- **Perimeter & Area:** Uses the artwork size plus mat borders to calculate the outside perimeter (for mouldings) and total area (for mats/glazing).
- **Markups:** Applies admin-configured multipliers (e.g., `cost * markup_moulding`).
- **Services:** Adds flat fees or dimensional fees (united inches, square inches) for shop labor.

### Export Engine
The app generates visual artifacts using Python libraries:
- **Pillow (PIL):** Used in `app/main.py` (`_export_quote_image`) to render a visual JPG mockup of the quote, drawing rectangles for the frame, mats, and pasting the cropped artwork.
- **ReportLab:** Used to generate formal PDF documents for Quotes, Work Orders, and Invoices.

## Frontend Architecture

### Monolithic SPA
The frontend does not use a framework like React or Vue. Instead, it relies on a single HTML file (`index.html`) and a massive JavaScript file (`app.js`).
- **State Management:** Global variables in `app.js` (e.g., `lastQuote`, `selectedMaterials`, `galleryMode`) act as the source of truth.
- **UI Updates:** DOM manipulation is done directly via `document.getElementById()` and `innerHTML` updates.
- **Workspaces:** The UI is divided into "workspaces" (Design, Gallery, Quotes, Admin). Switching workspaces toggles CSS `display: none` on main container divs.
- **Mockup Rendering:** The live framing mockup in the browser is built using layered DOM elements (`div` and `img`) styled with CSS to simulate mat reveals and frame widths. 

### Cropping & Metadata
When artwork is uploaded, `Cropper.js` is used to allow the operator to crop the image. Crucially, the app performs **non-destructive cropping**; it saves the crop coordinates (x, y, width, height) as JSON metadata in the `images` table. The mockup and export engines use this metadata to display the cropped version while preserving the original uploaded file.

## Design Philosophy & Constraints
1. **Local-First:** Operational data stays on the workstation. The backup system packages the database and generated assets for recovery.
2. **Speed over Modularity:** The monolithic JS/HTML approach allowed for rapid prototyping and iteration of the complex framing builder without boilerplate overhead, though it introduces technical debt for future scalability.
3. **Data Boundary:** There is a strict boundary between materials (mats/mouldings, imported from operator-supplied local catalog files) and shop services (labor/mounting, managed manually).
