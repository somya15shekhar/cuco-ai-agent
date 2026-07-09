# cuCO Agent API Backend

This is a FastAPI-based backend application integrated with Supabase for claim data management, authentication, and file storage.

## Features

1. **Claims Management (`POST /claims`)**:
   * Creates a medical/health claim in the database.
   * Mandates a valid `user_id` (representing the patient/user) to satisfy data integrity constraints.
   * Auto-generates a UUID for every claim.

2. **Document Upload (`POST /upload`)**:
   * Accepts a multipart form file (PDF, images, etc.) along with a `claim_id` (UUID) and `document_type`.
   * Uploads the file securely to the Supabase Storage bucket named `documents`.
   * Automatically handles duplicate file uploads by overwriting (upserting) existing files to prevent conflicts.
   * Inserts file metadata (`file_name`, `storage_path`, `mime_type`, etc.) into the `documents` database table, linking it directly to the corresponding claim.

3. **Secure Backend-to-Database Connection**:
   * Initialized with `SUPABASE_SERVICE_ROLE_KEY` to bypass RLS (Row-Level Security) restrictions, making trusted backend operations seamless.

4. **Auto-Generated Interactive Documentation**:
   * Built-in Swagger UI to test all API endpoints interactively.

---

## Getting Started

Follow these steps to run the project on your machine.

### Prerequisites

Make sure you have **Python 3.8+** installed.

### 1. Clone & Switch Branch
Clone the repository (or pull updates) and switch to the `arnab` branch:
```bash
git checkout arnab
```

### 2. Configure Environment Variables
Create a `.env` file in the project root directory (same folder as `main.py`) with your Supabase credentials:
```env
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

### 3. Install Dependencies
Navigate to the `backend` directory and install the required Python packages:
```bash
pip install -r backend/requirements.txt
```

### 4. Run the Server
From the `backend` directory, run the FastAPI server using `uvicorn`:
```bash
uvicorn app.main:app --reload
```

Once running, you can access the interactive API docs at:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## Testing the Upload Flow

1. **Create a Claim**:
   * Open the Swagger UI page.
   * Expand **POST `/claims`**, click **Try it out**, and **Execute** (make sure you have a valid user ID).
   * Copy the returned claim `"id"` (UUID).

2. **Upload a File**:
   * Expand **POST `/upload`**, click **Try it out**.
   * Paste the claim UUID into the `claim_id` field.
   * Select a PDF or image, and click **Execute**.
   * Verify the file in your Supabase Storage bucket under `documents` and in the `documents` database metadata table!
